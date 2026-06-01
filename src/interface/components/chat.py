# ==============================================================================
# chat.py — Chat Farmazzini Intel 2.0  |  Design refresh
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
import pandas as pd
import uuid
import boto3
import json
from datetime import datetime

from components.metrics import render_metrics
from utils.aws_client import (
    gerar_sql_com_bedrock,
    executar_via_step_functions,
    buscar_resultado_s3,
)


# ── Session init ──────────────────────────────────────────────────────────────

def _init_session():
    if "chats" not in st.session_state:
        pid = str(uuid.uuid4())[:8]
        st.session_state["chats"] = {
            pid: {
                "nome": "Análise Inicial",
                "historico": [],
                "criado_em": datetime.now().strftime("%H:%M"),
            }
        }
        st.session_state["chat_ativo"] = pid
    if "chat_ativo" not in st.session_state:
        st.session_state["chat_ativo"] = list(st.session_state["chats"].keys())[0]
    for key in ("exemplo_selecionado", "executar_exemplo"):
        if key not in st.session_state:
            st.session_state[key] = None if key == "exemplo_selecionado" else False


def _chat_atual():
    return st.session_state["chats"][st.session_state["chat_ativo"]]


def _novo_chat():
    nid = str(uuid.uuid4())[:8]
    n = len(st.session_state["chats"]) + 1
    st.session_state["chats"][nid] = {
        "nome": f"Nova Consulta #{n}",
        "historico": [],
        "criado_em": datetime.now().strftime("%H:%M"),
    }
    st.session_state["chat_ativo"] = nid


# ── Gráficos ──────────────────────────────────────────────────────────────────

def _render_grafico(df: pd.DataFrame, key: str):
    colunas_num = df.select_dtypes(include="number").columns.tolist()
    if not colunas_num:
        return
    with st.expander("📊 Gerar Gráfico", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo = st.selectbox("Tipo", ["Barras", "Linha", "Dispersão"], key=f"tipo_{key}")
        with c2:
            col_x = st.selectbox("Eixo X", df.columns.tolist(), key=f"x_{key}")
        with c3:
            col_y = st.selectbox("Eixo Y", colunas_num, key=f"y_{key}")

        if st.button("📈 Renderizar", key=f"render_{key}", type="primary"):
            df_plot = df[[col_x, col_y]].dropna().set_index(col_x)
            if tipo == "Barras":
                st.bar_chart(df_plot, color="#E63946")
            elif tipo == "Linha":
                st.line_chart(df_plot, color="#E63946")
            else:
                st.scatter_chart(df_plot)


# ── Render mensagem individual ────────────────────────────────────────────────

def _render_mensagem(msg: dict, idx: int):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="avatar-user">Você</div>
        <div class="chat-bubble-user">{msg["content"]}</div>
        """, unsafe_allow_html=True)

    elif msg["role"] == "assistant":
        st.markdown(f"""
        <div class="avatar-bot">💊 Farmazzini Intel</div>
        <div class="chat-bubble-assistant">{msg["content"]}</div>
        """, unsafe_allow_html=True)

        if msg.get("sql"):
            with st.expander("🗂️ Ver SQL gerado pelo Claude", expanded=False):
                st.code(msg["sql"], language="sql")

        if msg.get("df") is not None:
            render_metrics(msg["df"], key=str(idx))
            _render_grafico(msg["df"], key=str(idx))

            if st.button("⚡ Sugerir Contra-Ataque", key=f"ataque_{idx}"):
                st.session_state[f"mostrar_ataque_{idx}"] = True

            if st.session_state.get(f"mostrar_ataque_{idx}"):
                with st.spinner("✨ Claude analisando estratégia de contra-ataque…"):
                    df = msg["df"]
                    resumo = df.to_string(index=False, max_rows=5)
                    prompt_ataque = (
                        f"Com base nestes dados de mercado farmacêutico:\n{resumo}\n\n"
                        "Gere 2 planos de ação rápidos e práticos de marketing ou precificação "
                        "para a Farmazzini contra-atacar e preservar sua margem de lucro. "
                        "Seja direto, executivo e focado em táticas reais de farmácia. "
                        "Use negrito com ** para destacar pontos importantes."
                    )
                    client = boto3.client("bedrock-runtime", region_name="us-east-2")
                    body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 600,
                        "messages": [{"role": "user", "content": prompt_ataque}],
                    })
                    resp = client.invoke_model(
                        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                        body=body,
                    )
                    ataque = json.loads(resp["body"].read())["content"][0]["text"]

                ataque_fmt = (
                    ataque
                    .replace("\n", "<br>")
                    .replace("**", "<strong>", 1)
                )
                # Simpler but robust bold replace
                import re
                ataque_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", ataque)
                ataque_fmt = ataque_fmt.replace("\n", "<br>")

                st.markdown(f"""
                <div style="border-left:3px solid #E63946;padding:12px 16px;
                            background:rgba(230,57,70,0.05);border-radius:0 12px 12px 0;
                            margin-top:10px;font-size:13px;line-height:1.75;">
                    <strong style="color:#E63946;display:block;margin-bottom:8px;">
                        ⚡ Contra-Ataque Estratégico:
                    </strong>
                    {ataque_fmt}
                </div>
                """, unsafe_allow_html=True)

        elif msg.get("sem_dados"):
            st.warning("A consulta rodou com sucesso, mas não retornou registros.")


# ── Processamento da pergunta ─────────────────────────────────────────────────

def _processar_pergunta(user_input: str, filtros: dict):
    chat = _chat_atual()

    if not chat["historico"] and chat["nome"].startswith("Nova Consulta"):
        chat["nome"] = (user_input[:22] + "…") if len(user_input) > 22 else user_input

    chat["historico"].append({"role": "user", "content": user_input})

    with st.spinner("🧠 Claude Haiku 4.5 gerando o SQL…"):
        prompt = user_input
        if filtros.get("farmacia"):
            prompt = f"{user_input} (considere apenas a farmácia '{filtros['farmacia']}')"
        sql, erro = gerar_sql_com_bedrock(prompt)

    if erro:
        chat["historico"].append({
            "role": "assistant", "content": f"❌ Erro ao gerar SQL: `{erro}`",
            "sql": None, "df": None,
        })
        return

    with st.spinner("🛡️ Validando e executando no Athena…"):
        status, erro, status_resp = executar_via_step_functions(sql)

    if erro or status != "SUCCEEDED":
        chat["historico"].append({
            "role": "assistant",
            "content": f"❌ {erro or f'Status: `{status}`'}",
            "sql": sql, "df": None,
        })
        return

    with st.spinner("📦 Buscando dados no S3…"):
        df, erro = buscar_resultado_s3(status_resp)

    if erro:
        chat["historico"].append({
            "role": "assistant",
            "content": f"✅ Executado, mas erro ao carregar dados: `{erro}`",
            "sql": sql, "df": None,
        })
        return

    sem_dados = df is None or df.empty
    chat["historico"].append({
        "role": "assistant",
        "content": "✅ Consulta executada com sucesso!" if not sem_dados else "✅ Nenhum registro encontrado.",
        "sql": sql,
        "df": df if not sem_dados else None,
        "sem_dados": sem_dados,
    })


# ── Gerenciador de chats ──────────────────────────────────────────────────────

def _render_gerenciador_chats():
    chats = st.session_state["chats"]
    chat_ativo = st.session_state["chat_ativo"]

    col_busca, col_novo = st.columns([4, 1])
    with col_busca:
        busca = st.text_input(
            "busca",
            placeholder="🔍  Buscar chats…",
            label_visibility="collapsed",
            key="busca_chat_input",
        )
    with col_novo:
        if st.button("＋ Novo Chat", use_container_width=True):
            _novo_chat()
            st.rerun()

    ids_filtrados = [
        cid for cid, c in chats.items()
        if busca.lower() in c["nome"].lower()
    ]
    if not ids_filtrados:
        st.caption("Nenhum chat encontrado.")
        return

    cols = st.columns(min(len(ids_filtrados), 4))
    for i, cid in enumerate(ids_filtrados):
        c = chats[cid]
        ativo = cid == chat_ativo
        label = f"{'▶ ' if ativo else ''}{c['nome']}\n{c['criado_em']}"
        with cols[i % 4]:
            if st.button(
                label, key=f"sel_{cid}", use_container_width=True,
                type="primary" if ativo else "secondary",
            ):
                st.session_state["chat_ativo"] = cid
                st.rerun()


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def render_chat(filtros: dict):
    _init_session()

    # ── Cabeçalho ──────────────────────────────────────────────────────────────
    col_t, col_b = st.columns([3, 1])
    with col_t:
        st.markdown("""
        <div>
            <span style="font-family:'Space Grotesk',sans-serif;
                         font-size:1.75rem;font-weight:700;letter-spacing:2px;
                         text-transform:uppercase;">
                Farmazzini <span style="color:#E63946;">Intel</span>
            </span>
        </div>
        <p style="font-family:'DM Sans',sans-serif;color:#7a7a85;font-size:0.88rem;margin:2px 0 0;">
            Console de Inteligência de Mercado — Powered by Claude Haiku 4.5
        </p>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div style="text-align:right;padding-top:12px;">
            <span class="badge-green">✨ Bedrock Conectado</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Seletor de chats ────────────────────────────────────────────────────────
    _render_gerenciador_chats()
    st.markdown("---")

    chat = _chat_atual()

    # ── Ações do chat ativo ─────────────────────────────────────────────────────
    col_nome, col_del, col_exp = st.columns([3, 1, 1])
    with col_nome:
        novo_nome = st.text_input(
            "Renomear",
            value=chat["nome"],
            label_visibility="collapsed",
            placeholder="Nome do chat…",
            key=f"rename_{st.session_state['chat_ativo']}",
        )
        if novo_nome != chat["nome"]:
            chat["nome"] = novo_nome

    with col_del:
        if len(st.session_state["chats"]) > 1:
            if st.button("🗑️ Excluir", use_container_width=True):
                del st.session_state["chats"][st.session_state["chat_ativo"]]
                st.session_state["chat_ativo"] = list(st.session_state["chats"].keys())[0]
                st.rerun()

    with col_exp:
        if chat["historico"]:
            historico_txt = "\n\n".join([
                f"[{m['role'].upper()}] {m['content']}"
                + (f"\nSQL: {m['sql']}" if m.get("sql") else "")
                for m in chat["historico"]
            ])
            st.download_button(
                "💾 Exportar",
                data=historico_txt.encode("utf-8"),
                file_name=f"{chat['nome'][:20].replace(' ','_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"exp_{st.session_state['chat_ativo']}",
            )

    st.markdown("---")

    # ── Histórico de mensagens ──────────────────────────────────────────────────
    for idx, msg in enumerate(chat["historico"]):
        _render_mensagem(msg, idx)

    if chat["historico"]:
        st.markdown("---")
        if st.button("🗑️ Limpar conversa", key="limpar_conv"):
            chat["historico"] = []
            st.rerun()

    # ── Input ───────────────────────────────────────────────────────────────────
    executar_agora = st.session_state.pop("executar_exemplo", False)
    valor_inicial  = st.session_state.get("exemplo_selecionado") or ""
    if executar_agora:
        st.session_state["exemplo_selecionado"] = None

    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        user_input = st.text_input(
            label="Consulta",
            value=valor_inicial,
            placeholder="Faça uma consulta estratégica ao mercado…",
            label_visibility="collapsed",
            key="user_input_field",
        )
    with col_btn:
        executar = st.button("Analisar", type="primary", use_container_width=True)

    pergunta_final = user_input.strip() or valor_inicial.strip()
    if (executar or executar_agora) and pergunta_final:
        _processar_pergunta(pergunta_final, filtros)
        st.rerun()
    elif (executar or executar_agora) and not pergunta_final:
        st.warning("Digite uma consulta antes de executar.")
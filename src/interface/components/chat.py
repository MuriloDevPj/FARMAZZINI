# ==============================================================================
# chat.py — Componente principal do chat com múltiplas sessões e gráficos
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from components.metrics import render_metrics
from utils.aws_client import (
    gerar_sql_com_bedrock,
    executar_via_step_functions,
    buscar_resultado_s3,
)

# Import seguro do painel de alertas — não quebra o app se o módulo faltar
try:
    from utils.alertas import buscar_alertas_comerciais
    _ALERTAS_DISPONIVEL = True
except ImportError:
    _ALERTAS_DISPONIVEL = False


# ── Painel de Alertas (inline, sem dependência de arquivo externo) ────────────

def render_painel_alertas():
    if not _ALERTAS_DISPONIVEL:
        return

    if "alertas_comerciais" not in st.session_state:
        with st.spinner("🔍 Verificando alertas de mercado..."):
            try:
                st.session_state["alertas_comerciais"] = buscar_alertas_comerciais()
            except Exception:
                st.session_state["alertas_comerciais"] = []

    alertas = st.session_state.get("alertas_comerciais", [])

    if not alertas:
        st.info("✅ Nenhuma anomalia de preço detectada nas últimas 48 horas.")
        return

    st.markdown(f"### 🚨 Alertas Comerciais — {len(alertas)} anomalia(s) detectada(s)")

    for alerta in alertas:
        queda   = alerta.get("queda_pct", 0)
        ref     = alerta.get("preco_ref", 0)
        atual   = alerta.get("preco_concorrente", 0)
        diff    = alerta.get("diferenca_reais")
        ean     = alerta.get("ean", "—")
        ean_str = f"&nbsp;&nbsp;|&nbsp;&nbsp;EAN: <span style='color:#666;'>{ean}</span>" if ean and ean != "—" else ""
        diff_str = f"<div style='font-size:0.82rem;color:#F5A623;margin-top:0.4rem;'>⚡ Seu preço está R$ {diff:.2f} acima deles.</div>" if diff else ""

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#2E0D0D,#1A0A0A);
                    border:1px solid #8B1A1A;border-left:4px solid #C0392B;
                    border-radius:10px;padding:1rem 1.25rem;margin-bottom:0.75rem;">
            <div style="font-size:0.75rem;color:#888;text-transform:uppercase;
                        letter-spacing:0.08em;margin-bottom:0.4rem;">
                ⚠️ Alerta Comercial · {alerta.get('farmacia','')}
            </div>
            <div style="font-size:1rem;color:#F0F0F0;font-weight:600;">{alerta.get('nome','')}</div>
            <div style="font-size:0.85rem;color:#CCC;margin-top:0.3rem;">
                Queda de <span style="color:#FF6B6B;font-weight:700;">{queda:.1f}%</span>
                nas últimas 48h —
                de <span style="color:#AAA;">R$ {ref:.2f}</span>
                → <span style="color:#FF6B6B;font-weight:600;">R$ {atual:.2f}</span>
                {ean_str}
            </div>
            {diff_str}
        </div>
        """, unsafe_allow_html=True)

    if st.button("🔄 Atualizar alertas", key="btn_atualizar_alertas"):
        del st.session_state["alertas_comerciais"]
        st.rerun()


# ── Gerenciamento de sessões múltiplas ────────────────────────────────────────

def _init_session():
    if "chats" not in st.session_state:
        primeiro_id = str(uuid.uuid4())[:8]
        st.session_state["chats"] = {
            primeiro_id: {
                "nome": "Chat 1",
                "historico": [],
                "criado_em": datetime.now().strftime("%H:%M"),
            }
        }
        st.session_state["chat_ativo"] = primeiro_id

    if "chat_ativo" not in st.session_state or \
       st.session_state["chat_ativo"] not in st.session_state["chats"]:
        st.session_state["chat_ativo"] = list(st.session_state["chats"].keys())[0]

    st.session_state.setdefault("exemplo_selecionado", None)
    st.session_state.setdefault("executar_exemplo", False)


def _chat_atual() -> dict:
    return st.session_state["chats"][st.session_state["chat_ativo"]]


def _novo_chat():
    novo_id = str(uuid.uuid4())[:8]
    n = len(st.session_state["chats"]) + 1
    st.session_state["chats"][novo_id] = {
        "nome": f"Chat {n}",
        "historico": [],
        "criado_em": datetime.now().strftime("%H:%M"),
    }
    st.session_state["chat_ativo"] = novo_id


# ── Renderização de gráficos ──────────────────────────────────────────────────

def _tentar_grafico(df: pd.DataFrame, key: str):
    colunas_numericas = df.select_dtypes(include="number").columns.tolist()
    if not colunas_numericas:
        return

    with st.expander("📈 Gerar gráfico", expanded=False):
        tipo  = st.selectbox("Tipo de gráfico", ["Barras", "Linha", "Dispersão"], key=f"tipo_grafico_{key}")
        col_x = st.selectbox("Eixo X", df.columns.tolist(), key=f"eixo_x_{key}")
        col_y = st.selectbox("Eixo Y (valor)", colunas_numericas, key=f"eixo_y_{key}")

        if st.button("Gerar", key=f"btn_grafico_{key}"):
            df_plot = df[[col_x, col_y]].dropna().set_index(col_x)
            if tipo == "Barras":
                st.bar_chart(df_plot)
            elif tipo == "Linha":
                st.line_chart(df_plot)
            else:
                st.scatter_chart(df_plot)


# ── Renderização de mensagens ─────────────────────────────────────────────────

def _render_mensagem(msg: dict, idx: int):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="chat-bubble-user">
            <span style="font-size:0.7rem;color:#8B1A1A;font-weight:600;
                         text-transform:uppercase;letter-spacing:0.08em;">Você</span>
            <br>{msg["content"]}
        </div>
        """, unsafe_allow_html=True)

    elif msg["role"] == "assistant":
        st.markdown(f"""
        <div class="chat-bubble-assistant">
            <span style="font-size:0.7rem;color:#555;font-weight:600;
                         text-transform:uppercase;letter-spacing:0.08em;">💊 Farmazzini BI</span>
            <br>{msg["content"]}
        </div>
        """, unsafe_allow_html=True)

        if msg.get("sql"):
            with st.expander("📝 Ver SQL gerado pela IA", expanded=False):
                st.code(msg["sql"], language="sql")

        if msg.get("df") is not None:
            render_metrics(msg["df"], key=str(idx))
            _tentar_grafico(msg["df"], key=str(idx))
        elif msg.get("sem_dados"):
            st.warning("A consulta rodou com sucesso, mas não retornou registros.")


# ── Processamento da pergunta ─────────────────────────────────────────────────

def _processar_pergunta(user_input: str, filtros: dict):
    chat = _chat_atual()
    chat["historico"].append({"role": "user", "content": user_input})

    prompt_enriquecido = user_input
    if filtros.get("farmacia"):
        prompt_enriquecido = (
            f"{user_input} (considere apenas a farmácia '{filtros['farmacia']}')"
        )

    with st.spinner("🧠 Claude Haiku 4.5 gerando o SQL..."):
        sql, erro = gerar_sql_com_bedrock(prompt_enriquecido)

    if erro:
        chat["historico"].append({"role": "assistant", "content": f"❌ Erro ao gerar SQL: `{erro}`", "sql": None, "df": None})
        return

    with st.spinner("🛡️ Validando e executando no Athena..."):
        status, erro, status_resp = executar_via_step_functions(sql)

    if erro or status != "SUCCEEDED":
        mensagem = erro or f"Execução bloqueada. Status: `{status}`"
        chat["historico"].append({"role": "assistant", "content": f"❌ {mensagem}", "sql": sql, "df": None})
        return

    with st.spinner("📦 Buscando dados no S3..."):
        df, erro = buscar_resultado_s3(status_resp)

    if erro:
        chat["historico"].append({"role": "assistant", "content": f"✅ Consulta executada, mas erro ao carregar dados: `{erro}`", "sql": sql, "df": None})
        return

    sem_dados = df is None or df.empty
    chat["historico"].append({
        "role": "assistant",
        "content": "✅ Consulta executada com sucesso!" if not sem_dados else "✅ Nenhum registro correspondeu.",
        "sql": sql,
        "df": df if not sem_dados else None,
        "sem_dados": sem_dados,
    })


# ── Abas de chat ──────────────────────────────────────────────────────────────

def _render_abas():
    chats      = st.session_state["chats"]
    chat_ativo = st.session_state["chat_ativo"]
    ids        = list(chats.keys())

    cols = st.columns(len(ids) + 1)
    for i, cid in enumerate(ids):
        chat  = chats[cid]
        label = f"{'▶ ' if cid == chat_ativo else ''}{chat['nome']} {chat['criado_em']}"
        if cols[i].button(label, key=f"aba_{cid}", use_container_width=True):
            st.session_state["chat_ativo"] = cid
            st.rerun()

    if cols[-1].button("＋ Novo", key="btn_novo_chat", use_container_width=True):
        _novo_chat()
        st.rerun()


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def render_chat(filtros: dict):
    _init_session()

    st.markdown("""
    <div style="margin-bottom:1rem;">
        <h1 style="margin-bottom:0.15rem;">💊 Painel Inteligente de Mercado</h1>
        <p style="color:#666; font-size:0.9rem; margin:0;">
            Faça perguntas em português sobre os dados dos concorrentes.
        </p>
    </div>
    """, unsafe_allow_html=True)

    render_painel_alertas()
    st.markdown("---")

    _render_abas()
    st.markdown("---")

    chat = _chat_atual()

    for idx, msg in enumerate(chat["historico"]):
        _render_mensagem(msg, idx)

    if chat["historico"]:
        st.markdown("---")

    executar_agora = st.session_state.get("executar_exemplo", False)
    valor_inicial  = st.session_state.get("exemplo_selecionado") or ""
    if executar_agora:
        st.session_state["executar_exemplo"]    = False
        st.session_state["exemplo_selecionado"] = None

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            label="Pergunta",
            value=valor_inicial,
            placeholder="Ex: Qual o preço médio da dipirona?",
            label_visibility="collapsed",
            key="user_input_field",
        )
    with col_btn:
        executar = st.button("Analisar", type="primary", use_container_width=True)

    col_limpar, col_renomear, col_exportar = st.columns([1, 1, 1])

    with col_limpar:
        if chat["historico"]:
            if st.button("🗑️ Limpar", use_container_width=True):
                chat["historico"] = []
                st.rerun()

    with col_renomear:
        novo_nome = st.text_input(
            "Renomear chat",
            value=chat["nome"],
            key="renomear_chat",
            label_visibility="collapsed",
            placeholder="Nome do chat...",
        )
        if novo_nome and novo_nome != chat["nome"]:
            chat["nome"] = novo_nome

    with col_exportar:
        if chat["historico"]:
            historico_txt = "\n\n".join([
                f"[{m['role'].upper()}] {m['content']}"
                + (f"\nSQL: {m['sql']}" if m.get("sql") else "")
                for m in chat["historico"]
            ])
            st.download_button(
                "💾 Exportar",
                data=historico_txt.encode("utf-8"),
                file_name=f"{chat['nome'].replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"export_{st.session_state['chat_ativo']}",
            )

    pergunta_final = (user_input or valor_inicial).strip()
    if (executar or executar_agora) and pergunta_final:
        _processar_pergunta(pergunta_final, filtros)
        st.rerun()
    elif (executar or executar_agora) and not pergunta_final:
        st.warning("Por favor, preencha uma pergunta antes de executar.")
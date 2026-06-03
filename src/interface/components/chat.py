# ==============================================================================
# chat.py — Componente principal do chat e exibição de mensagens
# Projeto Farmazzini | Poli Júnior | Equipe 06
# Design: Farmazzini Intel (glassmorphism, Urbanist, #E63946)
# ==============================================================================

import streamlit as st
import pandas as pd
from components.metrics import render_metrics
from utils.aws_client import (
    gerar_sql_com_bedrock,
    executar_via_step_functions,
    buscar_resultado_s3,
)


def _init_session():
    if "historico" not in st.session_state:
        st.session_state["historico"] = []
    if "exemplo_selecionado" not in st.session_state:
        st.session_state["exemplo_selecionado"] = None
    if "executar_exemplo" not in st.session_state:
        st.session_state["executar_exemplo"] = False


def _render_mensagem(msg: dict, idx: int):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="chat-bubble-user">
            <span style="font-size:11px; color:rgba(255,255,255,0.7); font-weight:700;
                         text-transform:uppercase; letter-spacing:2px;">Você</span>
            <br>{msg["content"]}
        </div>
        """, unsafe_allow_html=True)

    elif msg["role"] == "assistant":
        st.markdown(f"""
        <div class="chat-bubble-assistant">
            <span style="font-size:11px; color:#E63946; font-weight:700;
                         text-transform:uppercase; letter-spacing:2px;">✦ Farmazzini Intel</span>
            <br><br>{msg["content"]}
        </div>
        """, unsafe_allow_html=True)

        if msg.get("sql"):
            with st.expander("📝 Ver SQL gerado pela IA", expanded=False):
                st.code(msg["sql"], language="sql")

        if msg.get("df") is not None:
            render_metrics(msg["df"], key=str(idx))
        elif msg.get("sem_dados"):
            st.warning("A consulta rodou com sucesso, mas não retornou registros para os filtros aplicados.")


def _processar_pergunta(user_input: str, filtros: dict):
    st.session_state["historico"].append({"role": "user", "content": user_input})

    # ── Passo A: Gerar SQL ─────────────────────────────────────────────────
    with st.spinner("🧠 Claude Haiku 4.5 gerando o SQL..."):
        prompt_enriquecido = user_input
        if filtros.get("farmacia"):
            prompt_enriquecido = f"{user_input} (considere apenas a farmácia '{filtros['farmacia']}')"
        sql, erro = gerar_sql_com_bedrock(prompt_enriquecido)

    if erro:
        st.session_state["historico"].append({
            "role": "assistant",
            "content": f"❌ Erro ao gerar SQL: `{erro}`",
            "sql": None, "df": None,
        })
        return

    # ── Passo B: Step Functions ────────────────────────────────────────────
    with st.spinner("🛡️ Validando e executando no Athena..."):
        status, erro, status_resp = executar_via_step_functions(sql)

    if erro or status != "SUCCEEDED":
        mensagem = erro or f"Execução bloqueada. Status: `{status}`"
        st.session_state["historico"].append({
            "role": "assistant",
            "content": f"❌ {mensagem}",
            "sql": sql, "df": None,
        })
        return

    # ── Passo C: S3 ───────────────────────────────────────────────────────
    with st.spinner("📦 Buscando dados no S3..."):
        df, erro = buscar_resultado_s3(status_resp)

    if erro:
        st.session_state["historico"].append({
            "role": "assistant",
            "content": f"✅ Consulta executada, mas erro ao carregar dados: `{erro}`",
            "sql": sql, "df": None,
        })
        return

    sem_dados = df is None or df.empty
    st.session_state["historico"].append({
        "role": "assistant",
        "content": "✅ Consulta executada com sucesso!" if not sem_dados
                   else "✅ Consulta executada, mas nenhum registro correspondeu.",
        "sql": sql,
        "df": df if not sem_dados else None,
        "sem_dados": sem_dados,
    })


def render_chat(filtros: dict):
    _init_session()

    # ── Cabeçalho estilo Intel ─────────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom:2rem;">
        <div style="font-size:13px; text-transform:uppercase; letter-spacing:3px;
                    color:#E63946; font-weight:700; margin-bottom:6px;">
            Intelligence Platform
        </div>
        <h1 style="margin:0; font-size:2rem; font-weight:700; letter-spacing:2px;">
            FARMAZZINI <span style="color:#E63946;">INTEL</span>
        </h1>
        <p style="color:#9a9a9f; font-size:0.88rem; margin:8px 0 0 0;">
            Faça perguntas em português sobre os dados dos concorrentes.
            A IA gera o SQL, valida e traz os resultados automaticamente.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Histórico de mensagens ─────────────────────────────────────────────
    for idx, msg in enumerate(st.session_state["historico"]):
        _render_mensagem(msg, idx)

    if st.session_state["historico"]:
        st.markdown("---")

    # ── Verifica exemplo clicado na sidebar ───────────────────────────────
    executar_agora = st.session_state.pop("executar_exemplo", False)
    valor_inicial  = st.session_state.get("exemplo_selecionado") or ""
    if executar_agora:
        st.session_state["exemplo_selecionado"] = None

    # ── Input ──────────────────────────────────────────────────────────────
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            label="Pergunta",
            value=valor_inicial,
            placeholder="Ex: Quais produtos da FarmaPonte têm cashback ativo?",
            label_visibility="collapsed",
            key="user_input_field",
        )
    with col_btn:
        executar = st.button("Analisar ✦", type="primary", use_container_width=True)

    if st.session_state["historico"]:
        if st.button("🗑️ Limpar conversa"):
            st.session_state["historico"] = []
            st.rerun()

    # ── Disparo ────────────────────────────────────────────────────────────
    pergunta_final = user_input.strip() or valor_inicial.strip()
    if (executar or executar_agora) and pergunta_final:
        _processar_pergunta(pergunta_final, filtros)
        st.rerun()
    elif (executar or executar_agora) and not pergunta_final:
        st.warning("Por favor, preencha uma pergunta antes de executar.")


# ==============================================================================
# formatar_resposta_html — usada pelo endpoint FastAPI do app.py
# Converte o DataFrame do Athena em HTML renderizável pelo chatbot externo
# ==============================================================================

def formatar_resposta_html(df: pd.DataFrame, pergunta: str) -> str:
    if df is None or df.empty:
        return "✅ Consulta executada, mas nenhum registro correspondeu aos filtros."

    if df.shape == (1, 1):
        valor  = df.iloc[0, 0]
        coluna = df.columns[0]
        return f"<strong>{coluna}:</strong> {valor}"

    MAX_LINHAS = 50
    truncado   = len(df) > MAX_LINHAS
    df_exibir  = df.head(MAX_LINHAS)

    colunas_html = "".join(f"<th>{col}</th>" for col in df_exibir.columns)
    cabecalho    = f"<thead><tr>{colunas_html}</tr></thead>"

    linhas_html = ""
    for _, row in df_exibir.iterrows():
        celulas      = "".join(f"<td>{val}</td>" for val in row)
        linhas_html += f"<tr>{celulas}</tr>"
    corpo = f"<tbody>{linhas_html}</tbody>"

    tabela = (
        '<div class="table-container">'
        f"<table>{cabecalho}{corpo}</table>"
        "</div>"
    )

    total = (
        f'<p style="font-size:12px; color:var(--text-muted); margin-top:6px;">'
        f"📊 <strong>{len(df_exibir)}</strong> registro(s) retornado(s).</p>"
    )

    aviso = ""
    if truncado:
        aviso = (
            f'<p style="font-size:12px; color:var(--text-muted); margin-top:4px;">'
            f"⚠️ Exibindo {MAX_LINHAS} de {len(df)} registros encontrados.</p>"
        )

    return tabela + total + aviso
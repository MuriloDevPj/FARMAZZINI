"""
Farmazzini Intel 2.0 — Console de Inteligência Estratégica
Desenvolvido com Streamlit + Claude (AWS Bedrock)

Estrutura:
    app.py                  → Entry point
    components/
        chat.py             → Interface de chat com IA
        metrics.py          → KPIs, tabelas e gráficos
        sidebar.py          → Barra lateral e navegação
    styles/
        custom.css          → Tema dark premium (Farmazzini)
    utils/
        aws_client.py       → Cliente AWS Bedrock (Claude)
        config.py           → Dados, prompts e configurações
"""

import streamlit as st
from pathlib import Path

# ── PAGE CONFIG (deve ser o 1º comando Streamlit) ────────────────────────────
st.set_page_config(
    page_title="Farmazzini Intel 2.0",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CARREGAR CSS CUSTOMIZADO ─────────────────────────────────────────────────
css_path = Path(__file__).parent / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── IMPORTS LOCAIS (após page_config) ────────────────────────────────────────
from components.sidebar import render_sidebar
from components.chat import render_chat
from components.metrics import render_metrics_bar, render_price_table, render_stock_chart
from utils.aws_client import is_bedrock_available

# ── INICIALIZAR SESSION STATE ────────────────────────────────────────────────
if "chats" not in st.session_state:
    st.session_state.chats = {
        "chat_1": {
            "title": "Análise de Preço: Dipirona",
            "messages": [],
        }
    }

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "chat_1"

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
db_filter, active_chat_id = render_sidebar()

# ── HEADER ───────────────────────────────────────────────────────────────────
header_col, status_col = st.columns([3, 2])

with header_col:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:16px; padding: 8px 0 4px 0;">
            <div class="logo-text">FARMAZZINI <span>INTEL</span></div>
            <span style="background:rgba(230,57,70,0.12); border:1px solid #E63946;
                         color:#E63946; padding:3px 8px; border-radius:4px;
                         font-size:10px; font-weight:700; letter-spacing:1px;">2.0</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with status_col:
    ai_status = "✨ Claude Conectado" if is_bedrock_available() else "🟡 Modo Demo"
    ai_color = "#10b981" if is_bedrock_available() else "#f59e0b"
    ai_bg = "rgba(16,185,129,0.15)" if is_bedrock_available() else "rgba(245,158,11,0.15)"

    st.markdown(
        f"""
        <div style="display:flex; justify-content:flex-end; align-items:center;
                    gap:12px; padding: 12px 0 4px 0;">
            <span style="background:{ai_bg}; border:1px solid {ai_color};
                         color:{ai_color}; padding:4px 12px; border-radius:4px;
                         font-size:11px; font-weight:700; letter-spacing:1px;">
                {ai_status}
            </span>
            <span style="font-size:12px; color:#9a9a9f;">
                Base: <strong style="color:#E63946;">{db_filter.title()}</strong>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<hr style='border-color:rgba(255,255,255,0.06); margin: 4px 0 16px 0;'>",
    unsafe_allow_html=True,
)

# ── LAYOUT PRINCIPAL: CHAT + PAINEL ──────────────────────────────────────────
chat_col, panel_col = st.columns([3, 2], gap="large")

with chat_col:
    render_chat(db_filter=db_filter, chat_id=active_chat_id)

with panel_col:
    # ── KPIs ─────────────────────────────────────────────────────────────────
    render_metrics_bar()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── PAINEL ANALÍTICO (COLLAPSIBLE) ────────────────────────────────────────
    with st.expander("📊 Tabela Comparativa de Preços", expanded=True):
        render_price_table(db_filter=db_filter)

    with st.expander("📦 Gráfico de Estoque", expanded=False):
        render_stock_chart()

    # ── DICA DE CONFIGURAÇÃO ──────────────────────────────────────────────────
    if not is_bedrock_available():
        st.markdown(
            """
            <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3);
                        border-radius:12px; padding:14px 16px; margin-top:12px; font-size:12px;
                        color:#f59e0b; line-height:1.6;">
                <strong>⚙️ Modo Demo Ativo</strong><br>
                Para ativar a IA real (Claude via AWS Bedrock), configure:<br>
                <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px;">
                AWS_ACCESS_KEY_ID</code><br>
                <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px;">
                AWS_SECRET_ACCESS_KEY</code><br>
                no arquivo <code>.streamlit/secrets.toml</code> ou variáveis de ambiente.
            </div>
            """,
            unsafe_allow_html=True,
        )
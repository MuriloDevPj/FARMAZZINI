# ==============================================================================
# app.py — Ponto de entrada principal da aplicação Farmazzini BI
# Como executar: cd src/interface && streamlit run app.py
# ==============================================================================

import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import streamlit as st

st.set_page_config(
    page_title="Farmazzini BI",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS do arquivo externo ────────────────────────────────────────────────────
_css_path = os.path.join(_here, "styles", "custom.css")
with open(_css_path, "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── CSS inline para forçar sidebar sempre visível ─────────────────────────────
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    display: flex !important;
    visibility: visible !important;
    width: 280px !important;
    min-width: 280px !important;
    transform: none !important;
}
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

from components.sidebar import render_sidebar
from components.chat import render_chat

filtros = render_sidebar()
render_chat(filtros)
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

# Injeta credenciais AWS vindas dos Secrets do Streamlit Cloud
os.environ["AWS_ACCESS_KEY_ID"]     = st.secrets.get("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_DEFAULT_REGION"]    = st.secrets.get("AWS_DEFAULT_REGION", "us-east-2")

# ── CSS do arquivo externo ────────────────────────────────────────────────────
_css_path = os.path.join(_here, "styles", "custom.css")
with open(_css_path, "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from components.sidebar import render_sidebar
from components.chat import render_chat

filtros = render_sidebar()
render_chat(filtros)
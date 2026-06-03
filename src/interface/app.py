# ==============================================================================
# app.py — Ponto de entrada principal da aplicação Farmazzini BI
# Como executar: cd src/interface && streamlit run app.py
# ==============================================================================

import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

# ==============================================================================
# Endpoint HTTP para o chatbot HTML (farmazzini_claude.html)
# Sobe FastAPI na porta 8502 em thread paralela ao Streamlit.
# O HTML envia: POST http://localhost:8502/consulta { pergunta, base }
# ==============================================================================
import threading
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import streamlit as st

from utils.aws_client import buscar_dados
from components.chat import formatar_resposta_html

_api = FastAPI()
_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # em produção, restrinja ao domínio do HTML
    allow_methods=["POST"],
    allow_headers=["*"],
)

@_api.post("/consulta")
async def consulta(request: Request):
    body     = await request.json()
    pergunta = body.get("pergunta", "").strip()
    base     = body.get("base", "todas")

    if not pergunta:
        return JSONResponse({"resposta": "⚠️ Pergunta vazia."}, status_code=400)

    resultado = buscar_dados(pergunta, base)

    if not resultado["sucesso"]:
        return JSONResponse({
            "resposta": f"❌ <strong>Erro no pipeline:</strong> {resultado['erro']}"
        })

    resposta_html = formatar_resposta_html(resultado["df"], pergunta)
    return JSONResponse({"resposta": resposta_html, "sql": resultado["sql"]})


def _iniciar_api():
    uvicorn.run(_api, host="0.0.0.0", port=8502, log_level="error")

# Garante que a thread só sobe uma vez (Streamlit re-executa o script a cada interação)
if "api_iniciada" not in st.session_state:
    t = threading.Thread(target=_iniciar_api, daemon=True)
    t.start()
    st.session_state["api_iniciada"] = True

# ─────────────────────────────────────────────────────────────────────────────

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
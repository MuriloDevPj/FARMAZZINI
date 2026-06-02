# ==============================================================================
# app.py — Farmazzini Intel 2.0  |  Console de Inteligência Estratégica
# Desenvolvido com Streamlit + Claude (AWS Bedrock)
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import sys
import os
from pathlib import Path

# Garante que o diretório raiz seja mapeado corretamente para evitar problemas de caminhos
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import streamlit as st

# ── PAGE CONFIG (Obrigatório ser o 1º comando Streamlit do script) ───────────
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

# ── IMPORTS LOCAIS CORRIGIDOS (Ajustados para refletir as funções reais) ─────
from components.sidebar import render_sidebar
from components.chat import render_chat
from components.metrics import render_metrics

# Verificação segura se o cliente do Bedrock consegue ser instanciado
def checar_conexao_bedrock():
    try:
        import boto3
        from utils.config import AWS_REGION
        client = boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)
        return True
    except Exception:
        return False

# ── INICIALIZAR SESSION STATE ────────────────────────────────────────────────
if "chats" not in st.session_state:
    st.session_state.chats = {
        "chat_1": {
            "nome": "Análise de Preço: Dipirona",
            "historico": [],
        }
    }

if "chat_ativo" not in st.session_state:
    st.session_state.chat_ativo = "chat_1"

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
# Captura o retorno estruturado da barra lateral (Dicionário contendo a farmácia selecionada)
filtros_sidebar = render_sidebar()

# Garante a extração segura do filtro de farmácia (padrão 'Todas') e o ID da conversa ativa
db_filter = filtros_sidebar.get("farmacia", "Todas") if isinstance(filtros_sidebar, dict) else "Todas"
active_chat_id = st.session_state.get("chat_ativo", "chat_1")

# ── HEADER ───────────────────────────────────────────────────────────────────
header_col, status_col = st.columns([3, 2])

with header_col:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:16px; padding: 8px 0 4px 0;">
            <div class="logo-text" style="font-family:'Space Grotesk', sans-serif; font-size:24px; font-weight:700; color:white;">
                FARMAZZINI <span style="color:#E63946;">INTEL</span>
            </div>
            <span style="background:rgba(230,57,70,0.12); border:1px solid #E63946;
                         color:#E63946; padding:3px 8px; border-radius:4px;
                         font-size:10px; font-weight:700; letter-spacing:1px;">2.0</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with status_col:
    bedrock_disponivel = checar_conexao_bedrock()
    ai_status = "✨ Claude Conectado" if bedrock_disponivel else "🟡 Modo Demo"
    ai_color = "#10b981" if bedrock_disponivel else "#f59e0b"
    ai_bg = "rgba(16,185,129,0.15)" if bedrock_disponivel else "rgba(245,158,11,0.15)"

    st.markdown(
        f"""
        <div style="display:flex; justify-content:flex-end; align-items:center;
                    gap:12px; padding: 12px 0 4px 0;">
            <span style="background:{ai_bg}; border:1px solid {ai_color};
                         color:{ai_color}; padding:4px 12px; border-radius:4px;
                         font-size:11px; font-weight:700; letter-spacing:1px;">
                {ai_status}
            </span>
            <span style="font-size:12px; color:#9a9a9f; font-family:'Space Grotesk', sans-serif;">
                Base: <strong style="color:#E63946;">{str(db_filter).title()}</strong>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<hr style='border-color:rgba(255,255,255,0.06); margin: 4px 0 16px 0;'>",
    unsafe_allow_html=True,
)

# ── LAYOUT PRINCIPAL: CONSOLE DE AUDITORIA UNIFICADO ─────────────────────────
# Como o módulo 'metrics.py' original do seu projeto renderiza os KPIs de forma acoplada
# junto com os resultados obtidos das queries do S3, o fluxo centralizado passa a rodar
# de forma linear no console principal de chats!
render_chat()

# ── PAINEL DE AVISO DE CONFIGURAÇÃO (Caso Bedrock não responda) ──────────────
if not bedrock_disponivel:
    st.markdown(
        """
        <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3);
                    border-radius:12px; padding:14px 16px; margin-top:25px; font-size:12px;
                    color:#f59e0b; line-height:1.6; font-family:'DM Sans', sans-serif;">
            <strong>⚙️ Modo Demo Ativo (AWS offline ou credenciais ausentes)</strong><br>
            Para ativar as chamadas de IA em tempo real ao Amazon Bedrock, certifique-se de configurar:<br>
            <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px;">AWS_ACCESS_KEY_ID</code> e 
            <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px;">AWS_SECRET_ACCESS_KEY</code>
            no arquivo de segredos do ambiente local.
        </div>
        """,
        unsafe_allow_html=True,
    )
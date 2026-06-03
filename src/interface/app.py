"""
╔══════════════════════════════════════════════════════════════════╗
║           FARMAZZINI INTEL — APP PRINCIPAL (STREAMLIT)          ║
║                                                                  ║
║  Este arquivo é o ponto de entrada da aplicação.                ║
║  Ele orquestra o design HTML + a lógica do pipeline de dados.   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os

# Garante que src/interface/ está no path — necessário no Streamlit Cloud
# onde o CWD pode ser a raiz do repo e não a pasta do app.py
sys.path.insert(0, os.path.dirname(__file__))


import streamlit as st
import streamlit.components.v1 as components
import json
from pipeline import processar_mensagem  # ← SEU PIPELINE ENTRA AQUI

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Farmazzini Intel",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Remove margens e padding padrão do Streamlit
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { padding: 0 !important; }
        [data-testid="stHeader"] { display: none !important; height: 0 !important; min-height: 0 !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        .stApp > header { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INICIALIZAÇÃO DO SESSION STATE
# ─────────────────────────────────────────────
if "chats" not in st.session_state:
    st.session_state.chats = [
        {
            "id": 1,
            "title": "Análise de Preço: Dipirona",
            "messages": [
                {
                    "sender": "bot",
                    "text": (
                        "Olá, Pedro! Seja bem-vindo ao <strong>Farmazzini Intel</strong>.<br><br>"
                        "Estou pronto para análises de <strong>estoque, preços, margens</strong> "
                        "e <strong>estratégias competitivas</strong>. Faça sua consulta abaixo!"
                    )
                }
            ]
        }
    ]

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = 1

if "active_db" not in st.session_state:
    st.session_state.active_db = "todas"

if "next_id" not in st.session_state:
    st.session_state.next_id = 2


# ─────────────────────────────────────────────
# COMPONENTE RECEPTOR DE postMessage
#
# Este HTML invisível (height=0) vive na página PAI do Streamlit
# (fora do iframe). Ele escuta mensagens do iframe filho e as
# repassa ao Streamlit gravando em st.session_state via
# st.components.v1.html com um truque de hash na URL —
# mas a forma mais confiável é usar o Streamlit >= 1.31
# com st.session_state + st.rerun() acionado por query_params
# setados na janela PAI (window.location, não window.location
# do iframe).
#
# Como funciona:
#   1. iframe chama window.parent.postMessage({type:'farmazzini_send', ...})
#   2. Este script escuta o evento na janela pai
#   3. Atualiza window.location.search na janela PAI (Streamlit)
#   4. Streamlit lê os query_params e faz st.rerun()
# ─────────────────────────────────────────────
RECEPTOR_HTML = """
<script>
(function() {
    // Evita registrar o listener múltiplas vezes
    if (window.__farmazzini_listener) return;
    window.__farmazzini_listener = true;

    window.addEventListener('message', function(event) {
        const d = event.data;
        if (!d || d.type !== 'farmazzini_send') return;

        // Monta os query params e navega na janela PAI (Streamlit)
        const url = new URL(window.location.href);
        url.searchParams.set('action',  d.action  || 'send');
        url.searchParams.set('msg',     d.msg     || '');
        url.searchParams.set('db',      d.db      || 'todas');
        url.searchParams.set('chat_id', d.chat_id || '');
        // Não enviamos chats_state — o Python usa seu próprio session_state
        window.location.href = url.toString();
    });
})();
</script>
"""
# height=0 → invisível, mas o script roda na página pai
components.html(RECEPTOR_HTML, height=0)


# ─────────────────────────────────────────────
# PROCESSAR AÇÃO DO USUÁRIO (BRIDGE HTML → PYTHON)
# ─────────────────────────────────────────────
params = st.query_params

if "action" in params:
    action = params.get("action")

    # ── ENVIAR MENSAGEM ──────────────────────────────────────
    if action == "send" and "msg" in params:
        user_msg = params.get("msg", "").strip()
        db_filter = params.get("db", "todas")

        if user_msg:
            st.session_state.active_db = db_filter

            chat = next((c for c in st.session_state.chats
                         if c["id"] == st.session_state.active_chat_id), None)

            if chat:
                chat["messages"].append({"sender": "user", "text": user_msg})

                if chat["title"].startswith("Nova Consulta"):
                    chat["title"] = user_msg[:20] + "..." if len(user_msg) > 20 else user_msg

                # ════════════════════════════════════════════
                # ▼▼▼  PONTO DE INTEGRAÇÃO DO SEU PIPELINE  ▼▼▼
                resposta = processar_mensagem(
                    mensagem=user_msg,
                    db_filter=db_filter,
                    historico=chat["messages"]
                )
                # ▲▲▲  PONTO DE INTEGRAÇÃO DO SEU PIPELINE  ▲▲▲
                # ════════════════════════════════════════════

                bot_text = f"""
                    {resposta}
                    <div class="action-row" style="margin-top:20px; border-top:1px solid var(--border); padding-top:12px;">
                        <button class="action-btn" onclick="exportCSV()">
                            <i class="fa-solid fa-file-csv"></i> 📥 Exportar CSV
                        </button>
                    </div>
                """
                chat["messages"].append({"sender": "bot", "text": bot_text})

    # ── NOVO CHAT ────────────────────────────────────────────
    elif action == "new_chat":
        new_id = st.session_state.next_id
        st.session_state.next_id += 1
        st.session_state.chats.append({
            "id": new_id,
            "title": f"Nova Consulta #{new_id}",
            "messages": [{"sender": "bot",
                           "text": "Nova sessão aberta. Como posso ajudar?"}]
        })
        st.session_state.active_chat_id = new_id

    # ── SELECIONAR CHAT ──────────────────────────────────────
    elif action == "select_chat" and "id" in params:
        st.session_state.active_chat_id = int(params.get("id"))

    # ── EXCLUIR CHAT ─────────────────────────────────────────
    elif action == "delete_chat" and "id" in params:
        del_id = int(params.get("id"))
        if len(st.session_state.chats) > 1:
            st.session_state.chats = [c for c in st.session_state.chats
                                       if c["id"] != del_id]
            if st.session_state.active_chat_id == del_id:
                st.session_state.active_chat_id = st.session_state.chats[0]["id"]

    # ── ALTERAR BASE DE DADOS ────────────────────────────────
    elif action == "set_db" and "db" in params:
        st.session_state.active_db = params.get("db")

    # Limpa os params e recarrega
    st.query_params.clear()
    st.rerun()


# ─────────────────────────────────────────────
# SERIALIZAR ESTADO PARA O HTML
# ─────────────────────────────────────────────
chats_json      = json.dumps(st.session_state.chats, ensure_ascii=False)
active_chat_id  = st.session_state.active_chat_id
active_db       = st.session_state.active_db


# ─────────────────────────────────────────────
# RENDERIZAR O HTML COMPLETO
# ─────────────────────────────────────────────
from ui import render_full_ui

html_content = render_full_ui(
    chats=chats_json,
    active_chat_id=active_chat_id,
    active_db=active_db
)

# ─────────────────────────────────────────────
# CSS — iframe ocupa 100dvh
# ─────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    header, footer {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
    }
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    .main, .block-container, .stApp {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
        background-color: #08030A !important;
        overflow: hidden !important;
        height: 100dvh !important;
        min-height: unset !important;
    }
    iframe {
        display: block !important;
        border: none !important;
        outline: none !important;
        width: 100vw !important;
        height: 100dvh !important;
        margin: 0 !important;
        padding: 0 !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

components.html(html_content, height=10000, scrolling=False)
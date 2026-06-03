"""
╔══════════════════════════════════════════════════════════════════╗
║           FARMAZZINI INTEL — APP PRINCIPAL (STREAMLIT)          ║
║                                                                  ║
║  Este arquivo é o ponto de entrada da aplicação.                ║
║  Ele orquestra o design HTML + a lógica do pipeline de dados.   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
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
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        footer { display: none !important; }

        html, body { margin: 0 !important; padding: 0 !important; overflow: hidden !important; }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
            height: 100vh !important;
            overflow: hidden !important;
        }
        [data-testid="stHtml"],
        [data-testid="stHtml"] > div {
            height: 100vh !important;
            overflow: hidden !important;
            padding: 0 !important;
            margin: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INICIALIZAÇÃO DO SESSION STATE
# Aqui ficam todos os dados que persistem entre
# interações do usuário sem recarregar a página.
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

if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

if "next_id" not in st.session_state:
    st.session_state.next_id = 2


# ─────────────────────────────────────────────
# PROCESSAR AÇÃO DO USUÁRIO (BRIDGE HTML → PYTHON)
#
# O HTML envia comandos via query_params.
# Aqui capturamos e processamos antes de renderizar.
# ─────────────────────────────────────────────
params = st.query_params

if "action" in params:
    action = params.get("action")

    # ── ENVIAR MENSAGEM ──────────────────────────────────────
    if action == "send" and "msg" in params:
        user_msg = params.get("msg", "").strip()
        db_filter = params.get("db", "todas")

        if user_msg:
            # Atualiza o db ativo
            st.session_state.active_db = db_filter

            # Encontra o chat ativo
            chat = next((c for c in st.session_state.chats
                         if c["id"] == st.session_state.active_chat_id), None)

            if chat:
                # Adiciona mensagem do usuário
                chat["messages"].append({"sender": "user", "text": user_msg})

                # Renomeia o chat se for novo
                if chat["title"].startswith("Nova Consulta"):
                    chat["title"] = user_msg[:20] + "..." if len(user_msg) > 20 else user_msg

                # ════════════════════════════════════════════════
                # ▼▼▼  PONTO DE INTEGRAÇÃO DO SEU PIPELINE  ▼▼▼
                #
                # A função processar_mensagem() está em pipeline.py
                # Ela recebe:
                #   - user_msg (str): texto da pergunta do usuário
                #   - db_filter (str): "todas" | "ponte" | "veracruz"
                #   - historico (list): lista de mensagens anteriores
                #
                # Retorna:
                #   - resposta (str): HTML ou texto da resposta
                # ════════════════════════════════════════════════
                resposta = processar_mensagem(
                    mensagem=user_msg,
                    db_filter=db_filter,
                    historico=chat["messages"]
                )

                # Adiciona a resposta do bot com botões de ação
                bot_text = f"""
                    {resposta}
                    <div class="action-row" style="margin-top:20px; border-top:1px solid var(--border); padding-top:12px;">
                        <button class="action-btn" onclick="triggerCSV()">
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
# Converte o session_state Python em JSON
# para injetar no JavaScript do HTML.
# ─────────────────────────────────────────────
chats_json = json.dumps(st.session_state.chats, ensure_ascii=False)
active_chat_id = st.session_state.active_chat_id
active_db = st.session_state.active_db


# ─────────────────────────────────────────────
# RENDERIZAR O HTML COMPLETO
# ─────────────────────────────────────────────
from ui import render_full_ui

html_content = render_full_ui(
    chats=chats_json,
    active_chat_id=active_chat_id,
    active_db=active_db
)

# Injeta o HTML via components — preserva 100% do design
st.html(html_content)
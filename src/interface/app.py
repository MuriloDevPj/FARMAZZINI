"""
╔══════════════════════════════════════════════════════════════════╗
║           FARMAZZINI INTEL — APP PRINCIPAL (STREAMLIT)          ║
║     VERSÃO COM LOGIN PERSISTENTE SEM DEPENDÊNCIAS EXTERNAS       ║
╚══════════════════════════════════════════════════════════════════╝

SOLUÇÃO DE PERSISTÊNCIA (sem biblioteca extra):
  O Streamlit reseta o session_state a cada rerun via query params.
  Em vez de cookies, usamos um token de sessão gravado em
  st.session_state E propagado no parâmetro 'state' que o JavaScript
  já envia a cada ação. O campo "auth" dentro desse JSON mantém
  o login vivo por toda a sessão sem precisar de nenhuma lib extra.
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components
import json
from pipeline import processar_mensagem

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Farmazzini Intel",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { padding: 0 !important; }
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }
        footer { display: none !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CREDENCIAIS
# ─────────────────────────────────────────────
VALID_USER = "Pedro Mazzini"
VALID_PASS = "@2026"

# ─────────────────────────────────────────────
# RESTAURAR ESTADO COMPLETO VIA QUERY PARAM 'state'
# O JavaScript já envia o estado serializado a cada ação.
# Incluímos "auth" nesse JSON para que o login sobreviva
# a todos os reruns sem precisar de cookies ou libs externas.
# ─────────────────────────────────────────────
_params = st.query_params
if "state" in _params:
    try:
        _s = json.loads(_params.get("state"))
        st.session_state.chats          = _s.get("chats",          st.session_state.get("chats", []))
        st.session_state.active_chat_id = _s.get("active_chat_id", st.session_state.get("active_chat_id", 1))
        st.session_state.active_db      = _s.get("active_db",      st.session_state.get("active_db", "todas"))
        st.session_state.next_id        = _s.get("next_id",        st.session_state.get("next_id", 2))
        # ← restaura autenticação embutida no state
        if _s.get("auth") is True:
            st.session_state.authenticated = True
    except (json.JSONDecodeError, Exception):
        pass

# Defaults iniciais
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "login_error" not in st.session_state:
    st.session_state.login_error = False
if "chats" not in st.session_state:
    st.session_state.chats = [
        {
            "id": 1,
            "title": "Análise de Preço: Dipirona",
            "messages": [
                {
                    "sender": "bot",
                    "text": (
                        "Olá! Seja bem-vindo ao <strong>Farmazzini Intel</strong>.<br><br>"
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
# TELA DE LOGIN
# ─────────────────────────────────────────────
def show_login():
    # ══════════════════════════════════════════════════════════════
    # CSS GLOBAL — fundo, inputs, botão, label nativo estilizado
    # Estratégia: usamos o label NATIVO do st.text_input (sem
    # label_visibility="collapsed") e o estilizamos via CSS.
    # Isso garante que label e input ficam sempre juntos no DOM,
    # eliminando os bugs de sobreposição de blocos.
    # O card é feito com st.container() estilizado via CSS.
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600;700&display=swap');

    /* ── Ocultar chrome do Streamlit ── */
    [data-testid="stHeader"],[data-testid="stToolbar"],
    [data-testid="stDecoration"],[data-testid="stStatusWidget"],
    header, footer { display: none !important; }

    /* ── Reset de layout ── */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .main, .block-container {
        padding: 0 !important; margin: 0 !important;
        max-width: 100% !important;
        background: transparent !important;
    }

    /* ── Fundo com gradientes radiais ── */
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse 80% 60% at 75% 5%,  #4a0c10 0%, transparent 60%),
            radial-gradient(ellipse 60% 50% at 20% 90%, #2a0608 0%, transparent 55%),
            #0e0102 !important;
        min-height: 100dvh !important;
    }

    /* ── Centralização vertical da página ── */
    [data-testid="stVerticalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 100dvh !important;
        padding: 32px 0 !important;
        gap: 0 !important;
    }

    /* ── Remove padding interno das colunas ── */
    [data-testid="stColumn"] { padding: 0 !important; }
    [data-testid="stColumn"] > div {
        padding: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
    }

    /* ══ CARD: estiliza o container nativo do Streamlit ══
       st.container() gera um div[data-testid="stVerticalBlockBorderWrapper"].
       Esse é o único jeito confiável de ter widgets DENTRO de um card
       no Streamlit — sem iframes, sem sobreposições. */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(15,4,5,0.88) !important;
        border: 1px solid rgba(255,255,255,0.09) !important;
        border-radius: 20px !important;
        padding: 28px 24px 24px !important;
        box-shadow: 0 8px 48px rgba(0,0,0,0.65), 0 1px 0 rgba(255,255,255,0.05) inset !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
    }
    /* Remove a borda padrão que o Streamlit coloca no container */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        border: none !important;
        padding: 0 !important;
    }

    /* ══ LABELS NATIVOS do st.text_input estilizados ══
       Usamos o label nativo (não ocultamos) e o transformamos
       nas labels uppercase do design. Isso mantém label + input
       sempre juntos no DOM — sem risco de sobreposição. */
    div[data-testid="stTextInput"] label {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        color: rgba(255,255,255,0.38) !important;
        margin-bottom: 4px !important;
    }

    /* ── Inputs ── */
    div[data-testid="stTextInput"] > div { position: relative !important; }
    div[data-testid="stTextInput"] input {
        background: rgba(0,0,0,0.45) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 12px !important;
        color: #fff !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 15px !important;
        padding: 14px 16px 14px 46px !important;
        height: 52px !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    div[data-testid="stTextInput"] input::placeholder { color: rgba(255,255,255,0.22) !important; }
    div[data-testid="stTextInput"] input:focus {
        border-color: rgba(212,48,48,0.6) !important;
        box-shadow: 0 0 0 3px rgba(212,48,48,0.14) !important;
        outline: none !important;
    }

    /* ── Ícone usuário (pelo placeholder) ── */
    div[data-testid="stTextInput"]:has(input[placeholder="Pedro Mazzini"]) > div::before {
        content: '';
        position: absolute !important; left: 15px !important; top: 50% !important;
        transform: translateY(-50%) !important;
        width: 18px !important; height: 18px !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23ffffff55' stroke-width='1.8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z'/%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important; background-size: contain !important;
        pointer-events: none !important; z-index: 10 !important;
    }

    /* ── Ícone senha ── */
    div[data-testid="stTextInput"]:has(input[placeholder="••••••"]) > div::before {
        content: '';
        position: absolute !important; left: 15px !important; top: 50% !important;
        transform: translateY(-50%) !important;
        width: 17px !important; height: 17px !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23ffffff55' stroke-width='1.8'%3E%3Crect x='3' y='11' width='18' height='11' rx='2'/%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M7 11V7a5 5 0 0 1 10 0v4'/%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important; background-size: contain !important;
        pointer-events: none !important; z-index: 10 !important;
    }

    /* ── Botão ── */
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #c8282a 0%, #8f1214 100%) !important;
        border: none !important; border-radius: 12px !important;
        color: #fff !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 15px !important; font-weight: 600 !important;
        width: 100% !important; height: 52px !important;
        padding: 0 !important; margin-top: 8px !important;
        box-shadow: 0 4px 24px rgba(180,20,20,0.35) !important;
        transition: opacity 0.18s, transform 0.12s !important;
        letter-spacing: 0.4px !important;
        cursor: pointer !important;
    }
    div[data-testid="stButton"] > button:hover  { opacity: 0.88 !important; transform: translateY(-1px) !important; }
    div[data-testid="stButton"] > button:active { opacity: 0.78 !important; transform: translateY(0) !important; }
    </style>
    """, unsafe_allow_html=True)

    # ══ COLUNA CENTRAL (centraliza tudo horizontalmente) ══
    _, col, _ = st.columns([1, 2.2, 1])

    with col:

        # ── CABEÇALHO (logo, badge, tagline) — HTML puro, sem widgets ──
        st.markdown("""
        <div style="text-align:center; margin-bottom:24px; font-family:'DM Sans',sans-serif;">
            <div style="display:inline-block; border:1px solid rgba(200,60,60,0.55);
                        border-radius:20px; padding:5px 18px; font-size:10px;
                        letter-spacing:2.5px; color:#c84040; text-transform:uppercase;
                        font-weight:600; margin-bottom:16px;">
                Inteligência de Mercado
            </div>
            <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; letter-spacing:6px;
                        color:#fff; line-height:1.0; text-shadow:0 2px 20px rgba(180,20,20,0.4);">
                FARMA<span style="color:#d43030;">ZZ</span>INI
            </div>
            <div style="font-size:13px; color:rgba(255,255,255,0.35); letter-spacing:0.5px; margin-top:8px;">
                Intel — Análise Competitiva em Tempo Real
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ══ CARD com st.container(border=True) ══
        # Todos os widgets ficam DENTRO deste container — sem sobreposições.
        with st.container(border=True):

            # Título e subtítulo
            st.markdown("""
            <div style="font-size:22px; font-weight:700; color:#fff; margin-bottom:4px;
                        font-family:'DM Sans',sans-serif; letter-spacing:-0.2px;
                        text-align:center;">
                Bem-vindo de volta
            </div>
            <div style="font-size:13px; color:rgba(255,255,255,0.38); margin-bottom:20px;
                        font-family:'DM Sans',sans-serif; text-align:center;">
                Faça login para acessar o painel de inteligência.
            </div>
            """, unsafe_allow_html=True)

            # Mensagem de erro (quando login falhar)
            if st.session_state.get("login_error", False):
                st.markdown("""
                <div style="background:rgba(200,30,30,0.16); border:1px solid rgba(200,30,30,0.38);
                            border-radius:10px; padding:11px 16px; font-size:13px; color:#f08080;
                            margin-bottom:12px; display:flex; align-items:center; gap:8px;
                            font-family:'DM Sans',sans-serif;">
                    <span>⚠</span><span>Usuário ou senha incorretos. Tente novamente.</span>
                </div>
                """, unsafe_allow_html=True)

            # Input usuário — label nativo "Usuário" estilizado via CSS
            username = st.text_input("Usuário", placeholder="Pedro Mazzini", key="login_user")

            # Input senha — label nativo "Senha" estilizado via CSS
            password = st.text_input("Senha", placeholder="••••••", type="password", key="login_pass")

            # Botão — use_container_width garante largura total
            if st.button("→  Entrar no painel", key="btn_login", use_container_width=True):
                if username == VALID_USER and password == VALID_PASS:
                    st.session_state.authenticated = True
                    st.session_state.login_error   = False
                    st.rerun()
                else:
                    st.session_state.login_error = True
                    st.rerun()

            # Divisor + rodapé (dentro do card)
            st.markdown("""
            <div style="display:flex; align-items:center; gap:12px; margin:24px 0 14px;">
                <div style="flex:1; height:1px; background:rgba(255,255,255,0.07);"></div>
                <span style="font-size:10px; color:rgba(255,255,255,0.22); letter-spacing:1.5px;
                             text-transform:uppercase; font-weight:600; font-family:'DM Sans',sans-serif;">
                    acesso restrito
                </span>
                <div style="flex:1; height:1px; background:rgba(255,255,255,0.07);"></div>
            </div>
            <div style="font-size:12px; color:rgba(255,255,255,0.25); text-align:center;
                        line-height:1.8; font-family:'DM Sans',sans-serif;">
                Plataforma exclusiva para a rede
                <span style="color:#d43030; font-weight:600;">Farmazzini</span>.<br>
                Em caso de dúvidas, contacte o administrador do sistema.
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CHATBOT PRINCIPAL
# ─────────────────────────────────────────────
def show_chatbot():
    params = st.query_params

    if "action" in params:
        action = params.get("action")

        if action == "send" and "msg" in params:
            user_msg  = params.get("msg", "").strip()
            db_filter = params.get("db", "todas")
            if user_msg:
                st.session_state.active_db = db_filter
                chat = next(
                    (c for c in st.session_state.chats if c["id"] == st.session_state.active_chat_id),
                    None
                )
                if chat:
                    ultima = chat["messages"][-1] if chat["messages"] else {}
                    ja_tem = (ultima.get("sender") == "user" and ultima.get("text") == user_msg)
                    if not ja_tem:
                        chat["messages"].append({"sender": "user", "text": user_msg})
                        if chat["title"].startswith("Nova Consulta"):
                            chat["title"] = (user_msg[:20] + "...") if len(user_msg) > 20 else user_msg
                        loading_html = """
                        <div class="loading-container" style="display:flex;align-items:center;padding:12px 18px;min-height:40px;">
                            <div class="dot-flashing"></div>
                        </div>
                        """
                        chat["messages"].append({
                            "sender": "bot",
                            "text": loading_html,
                            "is_loading": True,
                            "raw_query": user_msg,
                            "saved_db": db_filter
                        })

        elif action == "new_chat":
            new_id = st.session_state.next_id
            st.session_state.next_id += 1
            st.session_state.chats.append({
                "id": new_id,
                "title": f"Nova Consulta #{new_id}",
                "messages": [{"sender": "bot", "text": "Nova sessão aberta. Como posso ajudar?"}]
            })
            st.session_state.active_chat_id = new_id

        elif action == "select_chat" and "id" in params:
            try:
                st.session_state.active_chat_id = int(params.get("id"))
            except ValueError:
                pass

        elif action == "delete_chat" and "id" in params:
            try:
                del_id = int(params.get("id"))
                if len(st.session_state.chats) > 1:
                    st.session_state.chats = [c for c in st.session_state.chats if c["id"] != del_id]
                    if st.session_state.active_chat_id == del_id:
                        st.session_state.active_chat_id = st.session_state.chats[0]["id"]
            except ValueError:
                pass

        elif action == "set_db" and "db" in params:
            st.session_state.active_db = params.get("db")

        elif action == "logout":
            st.session_state.authenticated = False
            st.session_state.login_error   = False
            st.query_params.clear()
            st.rerun()

        st.query_params.clear()
        st.rerun()

    # ── SERIALIZAR ESTADO — inclui "auth" para persistir login entre reruns ──
    chats_json     = json.dumps(st.session_state.chats, ensure_ascii=False)
    active_chat_id = st.session_state.active_chat_id
    active_db      = st.session_state.active_db
    next_id        = st.session_state.next_id

    from ui import render_full_ui
    html_content = render_full_ui(
        chats=chats_json,
        active_chat_id=active_chat_id,
        active_db=active_db,
        next_id=next_id,
        auth=True,          # ← passa flag de autenticação para o JS injetar no state
    )

    st.markdown("""
    <style>
        [data-testid="stHeader"],[data-testid="stToolbar"],
        [data-testid="stDecoration"],[data-testid="stStatusWidget"],
        header, footer {
            display: none !important; height: 0 !important;
            min-height: 0 !important; visibility: hidden !important;
        }
        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"],
        .main, .block-container, .stApp {
            padding: 0 !important; margin: 0 !important;
            max-width: 100% !important; background-color: #08030A !important;
            overflow: hidden !important; height: 100dvh !important;
            min-height: unset !important;
        }
        iframe {
            display: block !important; border: none !important;
            width: 100vw !important; height: 100dvh !important;
            margin: 0 !important; padding: 0 !important;
            position: fixed !important; top: 0 !important; left: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    components.html(html_content, height=10000, scrolling=False)

    # ── SEGUNDO PLANO: PIPELINE DA AWS ──
    chat_atual = next(
        (c for c in st.session_state.chats if c["id"] == st.session_state.active_chat_id),
        None
    )
    if chat_atual and chat_atual["messages"]:
        ultima_msg = chat_atual["messages"][-1]
        if ultima_msg.get("is_loading") is True:
            start_time     = time.time()
            query_pendente = ultima_msg.get("raw_query")
            db_pendente    = ultima_msg.get("saved_db", "todas")

            resposta = processar_mensagem(
                mensagem=query_pendente,
                db_filter=db_pendente,
                historico=chat_atual["messages"][:-1]
            )

            tempo_minimo    = 3.5
            tempo_decorrido = time.time() - start_time
            if tempo_decorrido < tempo_minimo:
                time.sleep(tempo_minimo - tempo_decorrido)

            bot_text = f"\n            {resposta}\n        "
            chat_atual["messages"][-1] = {"sender": "bot", "text": bot_text}
            if "is_loading" in chat_atual["messages"][-1]:
                del chat_atual["messages"][-1]["is_loading"]

            st.rerun()


# ─────────────────────────────────────────────
# ROUTER PRINCIPAL
# ─────────────────────────────────────────────
if st.session_state.authenticated:
    show_chatbot()
else:
    show_login()
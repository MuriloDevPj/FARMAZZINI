"""
╔══════════════════════════════════════════════════════════════════╗
║           FARMAZZINI INTEL — APP PRINCIPAL (STREAMLIT)          ║
║              VERSÃO ULTRA-FLUIDA COM TRÊS PONTOS DE LOADING      ║
╚══════════════════════════════════════════════════════════════════╝
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

# ─────────────────────────────────────────────
# CREDENCIAIS DE ACESSO
# ─────────────────────────────────────────────
USUARIOS_VALIDOS = {
    "Pedro Mazzini": "@2026"
}

# ─────────────────────────────────────────────
# SESSION STATE — autenticação
# ─────────────────────────────────────────────
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "login_erro" not in st.session_state:
    st.session_state.login_erro = False

# ─────────────────────────────────────────────
# TELA DE LOGIN
# ─────────────────────────────────────────────
if not st.session_state.autenticado:

    # CSS: esconde tudo do Streamlit, deixa só o fundo e os widgets flutuando
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700;800&display=swap');

    /* ── Esconde chrome do Streamlit ── */
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    header, footer { display:none !important; }

    html, body,
    [data-testid="stAppViewContainer"],
    .main, .block-container, .stApp {
        padding: 0 !important;
        margin:  0 !important;
        max-width: 100% !important;
        overflow: hidden !important;
        height: 100dvh !important;
        background: transparent !important;
    }

    /* ── Fundo com gradientes animados ── */
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse 120% 80% at 50% -10%, rgba(180,20,45,0.38) 0%, rgba(80,0,18,0.20) 40%, transparent 70%),
            radial-gradient(ellipse 80%  60% at 85%  90%, rgba(120,0,25,0.28) 0%, transparent 60%),
            radial-gradient(ellipse 60%  50% at 10%  80%, rgba(160,15,35,0.18) 0%, transparent 55%),
            #08030A !important;
    }

    /* ── Centraliza o bloco de conteúdo ── */
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stAppViewBlockContainer"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        height: 100dvh !important;
        padding: 0 !important;
        gap: 0 !important;
    }

    /* ── Wrapper do card ── */
    .login-outer {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 32px;
        animation: cardIn 0.6s cubic-bezier(0.16,1,0.3,1) both;
        width: 420px;
    }
    @keyframes cardIn {
        from { opacity:0; transform:translateY(24px) scale(0.97); }
        to   { opacity:1; transform:translateY(0)    scale(1);    }
    }

    /* ── Marca ── */
    .login-brand {
        display:flex; flex-direction:column; align-items:center; gap:10px;
    }
    .brand-pill {
        background:rgba(232,37,58,0.12);
        border:1px solid rgba(232,37,58,0.28);
        border-radius:100px;
        padding:5px 16px;
        font-size:11px; font-weight:700; letter-spacing:2.5px;
        text-transform:uppercase; color:#E8253A;
        font-family:'Urbanist',sans-serif;
    }
    .brand-logo {
        font-size:32px; font-weight:800; letter-spacing:4px; color:#fff;
        font-family:'Urbanist',sans-serif; line-height:1;
    }
    .brand-logo .red { color:#E8253A; }
    .brand-sub {
        font-size:13px; color:#9a9a9f; font-weight:500; letter-spacing:0.5px;
        font-family:'Urbanist',sans-serif;
    }

    /* ── Card ── */
    .login-card {
        background:rgba(10,3,14,0.92);
        border:1px solid rgba(200,30,55,0.12);
        border-radius:28px;
        padding:40px 44px 36px;
        width:420px;
        backdrop-filter:blur(40px);
        box-shadow:
            0 32px 80px rgba(0,0,0,0.75),
            0 0 0 1px rgba(255,255,255,0.03),
            0 0 80px rgba(160,10,30,0.10);
    }
    .card-title {
        font-size:22px; font-weight:700; color:#fff; letter-spacing:0.3px;
        margin-bottom:6px; font-family:'Urbanist',sans-serif;
    }
    .card-desc {
        font-size:14px; color:#9a9a9f; margin-bottom:28px;
        font-family:'Urbanist',sans-serif;
    }
    .field-label {
        font-size:11px; font-weight:700; text-transform:uppercase;
        letter-spacing:1px; color:#9a9a9f; margin-bottom:8px; display:block;
        font-family:'Urbanist',sans-serif;
    }
    .error-box {
        background:rgba(232,37,58,0.10);
        border:1px solid rgba(232,37,58,0.35);
        border-radius:12px; padding:11px 16px;
        display:flex; align-items:center; gap:10px;
        font-size:13px; font-weight:500; color:#ff6b7a;
        margin-bottom:20px; font-family:'Urbanist',sans-serif;
        animation: shake 0.35s ease;
    }
    @keyframes shake {
        0%,100%{transform:translateX(0)}
        20%{transform:translateX(-5px)}
        40%{transform:translateX(5px)}
        60%{transform:translateX(-3px)}
        80%{transform:translateX(3px)}
    }
    .divider-line {
        display:flex; align-items:center; gap:12px;
        font-size:11px; color:rgba(154,154,159,0.4); font-weight:600;
        margin:20px 0; font-family:'Urbanist',sans-serif;
        text-transform:uppercase; letter-spacing:1px;
    }
    .divider-line::before, .divider-line::after {
        content:''; flex:1; height:1px; background:rgba(255,255,255,0.06);
    }
    .card-footer-txt {
        text-align:center; font-size:11px; color:rgba(154,154,159,0.45);
        line-height:1.7; font-family:'Urbanist',sans-serif; margin-top:20px;
    }
    .card-footer-txt strong { color:rgba(232,37,58,0.65); }

    /* ── Estiliza os inputs nativos do Streamlit ── */
    div[data-testid="stTextInput"] {
        margin-bottom: 16px !important;
    }
    div[data-testid="stTextInput"] label {
        display: none !important;
    }
    div[data-testid="stTextInput"] input {
        height: 52px !important;
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 14px !important;
        color: #fff !important;
        font-family: 'Urbanist', sans-serif !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        padding: 0 18px !important;
        caret-color: #E8253A !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: rgba(232,37,58,0.50) !important;
        box-shadow: 0 0 0 3px rgba(232,37,58,0.10) !important;
        background: rgba(232,37,58,0.04) !important;
    }
    div[data-testid="stTextInput"] input::placeholder {
        color: rgba(154,154,159,0.45) !important;
    }
    /* Botão nativo do Streamlit → estilo primário vermelho */
    div[data-testid="stButton"] button {
        height: 54px !important;
        width: 100% !important;
        background: linear-gradient(135deg, #E8253A 0%, #C01535 40%, #8B0828 100%) !important;
        border: 1px solid rgba(255,80,100,0.20) !important;
        border-radius: 16px !important;
        color: #fff !important;
        font-family: 'Urbanist', sans-serif !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 8px 28px rgba(200,20,50,0.40),
                    0 2px 8px rgba(230,40,60,0.25),
                    inset 0 1px 0 rgba(255,120,140,0.18) !important;
        transition: all 0.25s !important;
        margin-top: 4px !important;
    }
    div[data-testid="stButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 14px 36px rgba(200,20,50,0.55) !important;
    }
    div[data-testid="stButton"] button p {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #fff !important;
    }
    /* Remove borda azul de foco padrão do Streamlit */
    div[data-testid="stButton"] button:focus {
        box-shadow: 0 8px 28px rgba(200,20,50,0.40) !important;
        outline: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Marca (HTML puro, só visual) ──
    st.markdown("""
    <div class="login-outer">
        <div class="login-brand">
            <div class="brand-pill">Inteligência de Mercado</div>
            <div class="brand-logo">FARM<span class="red">A</span>Z<span class="red">Z</span>INI</div>
            <div class="brand-sub">Intel &mdash; Análise Competitiva em Tempo Real</div>
        </div>
    """, unsafe_allow_html=True)

    # ── Abertura do card ──
    st.markdown("""
    <div class="login-card">
        <div class="card-title">Bem-vindo 👋</div>
        <div class="card-desc">Faça login para acessar o painel de inteligência.</div>
        <span class="field-label">Usuário</span>
    """, unsafe_allow_html=True)

    # ── Inputs NATIVOS do Streamlit (funcionam no Streamlit Cloud) ──
    usuario_input = st.text_input("usuario_label", placeholder="Seu nome de usuário",
                                   key="login_user_input", label_visibility="collapsed")

    st.markdown('<span class="field-label">Senha</span>', unsafe_allow_html=True)

    senha_input = st.text_input("senha_label", placeholder="Sua senha de acesso",
                                 type="password", key="login_pass_input",
                                 label_visibility="collapsed")

    # Erro de credenciais
    if st.session_state.login_erro:
        st.markdown("""
        <div class="error-box">
            ⚠️&nbsp; Usuário ou senha inválidos. Tente novamente.
        </div>
        """, unsafe_allow_html=True)

    # Botão NATIVO do Streamlit
    entrar = st.button("→  Entrar no painel", key="btn_login", use_container_width=True)

    st.markdown("""
        <div class="divider-line">acesso restrito</div>
        <div class="card-footer-txt">
            Plataforma exclusiva para a rede <strong>Farmazzini</strong>.<br>
            Em caso de dúvidas, contacte o administrador do sistema.
        </div>
    </div></div>
    """, unsafe_allow_html=True)

    # ── Lógica de autenticação ──
    if entrar:
        if USUARIOS_VALIDOS.get(usuario_input.strip()) == senha_input:
            st.session_state.autenticado = True
            st.session_state.usuario_logado = usuario_input.strip()
            st.session_state.login_erro = False
            st.rerun()
        else:
            st.session_state.login_erro = True
            st.rerun()

    st.stop()

# ─────────────────────────────────────────────
# A PARTIR DAQUI: CHATBOT ORIGINAL (sem alterações)
# ─────────────────────────────────────────────

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
# SESSION STATE
# ─────────────────────────────────────────────
_params_init = st.query_params
if "state" in _params_init:
    try:
        _state = json.loads(_params_init.get("state"))
        st.session_state.chats         = _state.get("chats",         st.session_state.get("chats", []))
        st.session_state.active_chat_id = _state.get("active_chat_id", st.session_state.get("active_chat_id", 1))
        st.session_state.active_db      = _state.get("active_db",      st.session_state.get("active_db", "todas"))
        st.session_state.next_id        = _state.get("next_id",        st.session_state.get("next_id", 2))
    except (json.JSONDecodeError, Exception):
        pass

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
# PROCESSAR AÇÃO VIA QUERY PARAMS
# ─────────────────────────────────────────────
params = st.query_params

if "action" in params:
    action = params.get("action")

    if action == "send" and "msg" in params:
        user_msg  = params.get("msg", "").strip()
        db_filter = params.get("db", "todas")

        if user_msg:
            st.session_state.active_db = db_filter

            chat = next(
                (c for c in st.session_state.chats
                 if c["id"] == st.session_state.active_chat_id),
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
                    <div class="loading-container" style="display: flex; align-items: center; padding: 12px 18px; min-height: 40px;">
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
                st.session_state.chats = [
                    c for c in st.session_state.chats if c["id"] != del_id
                ]
                if st.session_state.active_chat_id == del_id:
                    st.session_state.active_chat_id = st.session_state.chats[0]["id"]
        except ValueError:
            pass

    elif action == "set_db" and "db" in params:
        st.session_state.active_db = params.get("db")

    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────────
# SERIALIZAR ESTADO
# ─────────────────────────────────────────────
chats_json     = json.dumps(st.session_state.chats, ensure_ascii=False)
active_chat_id = st.session_state.active_chat_id
active_db      = st.session_state.active_db
next_id        = st.session_state.next_id

# ─────────────────────────────────────────────
# RENDERIZAR HTML
# ─────────────────────────────────────────────
from ui import render_full_ui

html_content = render_full_ui(
    chats=chats_json,
    active_chat_id=active_chat_id,
    active_db=active_db,
    next_id=next_id,
)

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

# ─────────────────────────────────────────────
# PIPELINE AWS (SEGUNDO PLANO)
# ─────────────────────────────────────────────
chat_atual = next(
    (c for c in st.session_state.chats if c["id"] == st.session_state.active_chat_id),
    None
)

if chat_atual and chat_atual["messages"]:
    ultima_msg = chat_atual["messages"][-1]

    if ultima_msg.get("is_loading") is True:
        start_time = time.time()

        query_pendente = ultima_msg.get("raw_query")
        db_pendente = ultima_msg.get("saved_db", "todas")

        resposta = processar_mensagem(
            mensagem=query_pendente,
            db_filter=db_pendente,
            historico=chat_atual["messages"][:-1]
        )

        tempo_minimo = 3.5
        tempo_decorrido = time.time() - start_time
        if tempo_decorrido < tempo_minimo:
            time.sleep(tempo_minimo - tempo_decorrido)

        bot_text = f"""
            {resposta}
        """

        chat_atual["messages"][-1] = {"sender": "bot", "text": bot_text}

        if "is_loading" in chat_atual["messages"][-1]:
            del chat_atual["messages"][-1]["is_loading"]

        st.rerun()
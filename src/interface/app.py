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
# CORREÇÃO COMPLETA:
#   - Removido localStorage (causava loop infinito de redirect)
#   - Removido token hash (desnecessário para este fluxo)
#   - Lógica simplificada: query_params → session_state → rerun
# ─────────────────────────────────────────────
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "login_erro" not in st.session_state:
    st.session_state.login_erro = False

_params_auth = st.query_params
if not st.session_state.autenticado and _params_auth.get("action") == "login":
    _u = _params_auth.get("usr", "").strip()
    _p = _params_auth.get("pwd", "")
    if USUARIOS_VALIDOS.get(_u) == _p:
        st.session_state.autenticado    = True
        st.session_state.usuario_logado = _u
        st.session_state.login_erro     = False
    else:
        st.session_state.login_erro = True
    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────────
# TELA DE LOGIN
# ─────────────────────────────────────────────
if not st.session_state.autenticado:

    erro_html = ""
    if st.session_state.login_erro:
        erro_html = """
        <div class="err-box">
            ⚠️&nbsp;&nbsp;Usuário ou senha inválidos. Tente novamente.
        </div>
        """

    login_page = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{ box-sizing:border-box; margin:0; padding:0; }}
html, body {{
    font-family: 'Urbanist', sans-serif;
    height: 100%; width: 100%;
    background: transparent;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
}}

/* Glows */
.glow-orb {{ position:fixed; pointer-events:none; border-radius:50%; z-index:0; }}
.glow-orb-1 {{
    top:-20%; left:15%; width:70vw; height:70vw;
    background: radial-gradient(ellipse at center, rgba(220,30,55,0.30) 0%, rgba(140,5,30,0.18) 35%, rgba(80,0,15,0.08) 60%, transparent 80%);
    filter: blur(90px);
    animation: drift1 12s ease-in-out infinite alternate;
}}
.glow-orb-2 {{
    bottom:-15%; right:5%; width:55vw; height:55vw;
    background: radial-gradient(ellipse at center, rgba(160,10,35,0.22) 0%, rgba(90,0,20,0.12) 40%, transparent 70%);
    filter: blur(110px);
    animation: drift2 15s ease-in-out infinite alternate;
}}
@keyframes drift1 {{ from{{transform:translate(0,0) scale(1)}} to{{transform:translate(3vw,2vh) scale(1.08)}} }}
@keyframes drift2 {{ from{{transform:translate(0,0) scale(1)}} to{{transform:translate(-2vw,-3vh) scale(1.05)}} }}

/* Wrapper */
.login-wrapper {{
    display:flex; flex-direction:column; align-items:center;
    gap:28px; width:440px; position:relative; z-index:2;
    animation: cardIn 0.65s cubic-bezier(0.16,1,0.3,1) both;
}}
@keyframes cardIn {{
    from {{ opacity:0; transform:translateY(28px) scale(0.97); }}
    to   {{ opacity:1; transform:translateY(0)    scale(1);    }}
}}

/* Marca */
.login-brand {{ display:flex; flex-direction:column; align-items:center; gap:10px; }}
.brand-pill {{
    background: rgba(232,37,58,0.12);
    border: 1px solid rgba(232,37,58,0.28);
    border-radius: 100px; padding: 5px 18px;
    font-size: 11px; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase; color: #E8253A;
}}
.brand-logo {{
    font-size: 36px; font-weight: 800; letter-spacing: 5px; color: #fff; line-height: 1;
}}
.brand-logo .zz {{ color: #E8253A; }}
.brand-sub {{ font-size: 13px; color: #9a9a9f; font-weight: 500; letter-spacing: 0.5px; }}

/* Card */
.login-card {{
    background: rgba(10,3,14,0.93);
    border: 1px solid rgba(200,30,55,0.14);
    border-radius: 28px;
    padding: 40px 44px 36px;
    width: 440px;
    backdrop-filter: blur(40px);
    box-shadow:
        0 32px 80px rgba(0,0,0,0.80),
        0 0 0 1px rgba(255,255,255,0.03),
        0 0 100px rgba(160,10,30,0.12),
        inset 0 1px 0 rgba(255,255,255,0.04);
}}
.card-title {{ font-size: 22px; font-weight: 700; color: #fff; margin-bottom: 6px; }}
.card-desc  {{ font-size: 14px; color: #9a9a9f; margin-bottom: 28px; }}
.field-lbl  {{
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #9a9a9f; margin-bottom: 8px;
    display: block;
}}
.field-lbl-2 {{
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #9a9a9f; margin-bottom: 8px; margin-top: 20px;
    display: block;
}}

/* Inputs */
.field-wrap {{ position: relative; }}
.field-icon {{
    position: absolute; left: 16px; top: 50%; transform: translateY(-50%);
    color: rgba(154,154,159,0.5); font-size: 16px; pointer-events: none;
}}
.field-wrap input {{
    width: 100%; height: 52px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    color: #fff; font-family: 'Urbanist', sans-serif;
    font-size: 15px; font-weight: 500;
    padding: 0 48px 0 46px;
    caret-color: #E8253A;
    outline: none;
    transition: border-color 0.25s, box-shadow 0.25s, background 0.25s;
}}
.field-wrap input:focus {{
    border-color: rgba(232,37,58,0.55);
    box-shadow: 0 0 0 3px rgba(232,37,58,0.10);
    background: rgba(232,37,58,0.04);
}}
.field-wrap input::placeholder {{ color: rgba(154,154,159,0.40); }}

/* Toggle senha */
.toggle-eye {{
    position: absolute; right: 16px; top: 50%; transform: translateY(-50%);
    color: rgba(154,154,159,0.5); cursor: pointer; font-size: 16px;
    transition: color 0.2s;
}}
.toggle-eye:hover {{ color: #E8253A; }}

/* Erro */
.err-box {{
    background: rgba(232,37,58,0.10);
    border: 1px solid rgba(232,37,58,0.35);
    border-radius: 12px; padding: 12px 16px;
    display: flex; align-items: center; gap: 10px;
    font-size: 13px; font-weight: 500; color: #ff6b7a;
    margin-bottom: 20px;
    animation: shake 0.38s ease;
}}
@keyframes shake {{
    0%,100%{{transform:translateX(0)}}
    20%{{transform:translateX(-6px)}}
    40%{{transform:translateX(6px)}}
    60%{{transform:translateX(-4px)}}
    80%{{transform:translateX(4px)}}
}}

/* Botão */
.btn-login {{
    width: 100%; height: 54px; margin-top: 28px;
    background: linear-gradient(135deg, #E8253A 0%, #C01535 40%, #8B0828 100%);
    border: 1px solid rgba(255,80,100,0.22);
    border-radius: 16px;
    color: #fff; font-family: 'Urbanist', sans-serif;
    font-size: 16px; font-weight: 700; letter-spacing: 0.5px;
    cursor: pointer;
    box-shadow:
        0 8px 28px rgba(200,20,50,0.42),
        0 2px 8px rgba(230,40,60,0.25),
        inset 0 1px 0 rgba(255,120,140,0.18);
    transition: transform 0.22s, box-shadow 0.22s;
    display: flex; align-items: center; justify-content: center; gap: 10px;
}}
.btn-login:hover {{
    transform: translateY(-2px);
    box-shadow: 0 14px 36px rgba(200,20,50,0.58), 0 4px 12px rgba(230,40,60,0.32);
}}
.btn-login:active {{ transform: translateY(0); }}
.btn-login .spinner {{
    width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff; border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: none;
}}
.btn-login.loading .spinner {{ display: block; }}
.btn-login.loading .btn-text {{ opacity: 0.7; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}

/* Divisor + rodapé */
.divider-row {{
    display: flex; align-items: center; gap: 12px;
    font-size: 11px; color: rgba(154,154,159,0.4); font-weight: 600;
    margin: 20px 0 0; text-transform: uppercase; letter-spacing: 1px;
}}
.divider-row::before, .divider-row::after {{
    content:''; flex:1; height:1px; background: rgba(255,255,255,0.06);
}}
.card-foot {{
    text-align: center; font-size: 11px; color: rgba(154,154,159,0.45);
    line-height: 1.75; margin-top: 16px;
}}
.card-foot strong {{ color: rgba(232,37,58,0.70); font-weight: 700; }}
</style>
</head>
<body>

<div class="glow-orb glow-orb-1"></div>
<div class="glow-orb glow-orb-2"></div>

<div class="login-wrapper">

    <!-- Marca -->
    <div class="login-brand">
        <div class="brand-pill">Inteligência de Mercado</div>
        <div class="brand-logo">FARMA<span class="zz">ZZ</span>INI</div>
        <div class="brand-sub">Intel &mdash; Análise Competitiva em Tempo Real</div>
    </div>

    <!-- Card -->
    <div class="login-card">
        <div class="card-title">Bem-vindo de volta 👋</div>
        <div class="card-desc">Faça login para acessar o painel de inteligência.</div>

        {erro_html}

        <span class="field-lbl">Usuário</span>
        <div class="field-wrap">
            <span class="field-icon">&#9901;</span>
            <input id="inp-user" type="text" placeholder="Seu nome de usuário" autocomplete="username" autofocus>
        </div>

        <span class="field-lbl-2">Senha</span>
        <div class="field-wrap">
            <span class="field-icon">&#128274;</span>
            <input id="inp-pass" type="password" placeholder="Sua senha de acesso" autocomplete="current-password">
            <span class="toggle-eye" id="eye-toggle" onclick="toggleSenha()">&#128065;</span>
        </div>

        <button class="btn-login" id="btn-login" onclick="fazerLogin()">
            <div class="spinner"></div>
            <span class="btn-text">&#8594;&nbsp; Entrar no painel</span>
        </button>

        <div class="divider-row">acesso restrito</div>
        <div class="card-foot">
            Plataforma exclusiva para a rede <strong>Farmazzini</strong>.<br>
            Em caso de dúvidas, contacte o administrador do sistema.
        </div>
    </div>

</div>

<script>
// Permite enviar com Enter
document.getElementById('inp-user').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') document.getElementById('inp-pass').focus();
}});
document.getElementById('inp-pass').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') fazerLogin();
}});

function toggleSenha() {{
    var inp = document.getElementById('inp-pass');
    inp.type = inp.type === 'password' ? 'text' : 'password';
}}

function fazerLogin() {{
    var btn  = document.getElementById('btn-login');
    var user = document.getElementById('inp-user').value.trim();
    var pass = document.getElementById('inp-pass').value;
    if (!user || !pass) return;

    btn.classList.add('loading');
    btn.disabled = true;

    // CORREÇÃO FINAL: usa window.parent.location.href com pathname completo
    // para forçar um reload real da página pai. Apenas .search não funciona
    // dentro de iframe (Streamlit usa components.html que cria iframe isolado).
    var params = new URLSearchParams({{
        action: 'login',
        usr:    user,
        pwd:    pass
    }});
    window.parent.location.href = window.parent.location.pathname + '?' + params.toString();
}}
</script>
</body>
</html>"""

    components.html(login_page, height=10000, scrolling=False)
    st.markdown("""
    <style>
    [data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
    [data-testid="stStatusWidget"],header,footer{{display:none!important;}}
    html,body,[data-testid="stAppViewContainer"],[data-testid="stAppViewBlockContainer"],
    [data-testid="stVerticalBlock"],[data-testid="stVerticalBlockBorderWrapper"],
    .main,.block-container,.stApp{{
        padding:0!important;margin:0!important;max-width:100%!important;
        background-color:#08030A!important;overflow:hidden!important;
        height:100dvh!important;min-height:unset!important;
    }}
    iframe{{display:block!important;border:none!important;width:100vw!important;
        height:100dvh!important;margin:0!important;padding:0!important;
        position:fixed!important;top:0!important;left:0!important;}}
    </style>
    """, unsafe_allow_html=True)

    st.stop()

# ═══════════════════════════════════════════════════════
# A PARTIR DAQUI: CHATBOT ORIGINAL (sem alterações)
# ═══════════════════════════════════════════════════════

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

        chat_atual["messages"][-1] = {"sender": "bot", "text": f"\n            {resposta}\n        "}

        if "is_loading" in chat_atual["messages"][-1]:
            del chat_atual["messages"][-1]["is_loading"]

        st.rerun()
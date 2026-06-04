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
    # Oculta todos os elementos do Streamlit e prepara o fundo
    st.markdown("""
    <style>
    [data-testid="stHeader"],[data-testid="stToolbar"],
    [data-testid="stDecoration"],[data-testid="stStatusWidget"],
    header, footer { display: none !important; }
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    .main, .block-container, .stApp {
        padding: 0 !important; margin: 0 !important;
        max-width: 100% !important; overflow: hidden !important;
        height: 100dvh !important; min-height: unset !important;
        background: transparent !important;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse 80% 60% at 75% 5%,  #4a0c10 0%, transparent 60%),
            radial-gradient(ellipse 60% 50% at 20% 90%, #2a0608 0%, transparent 55%),
            #0e0102 !important;
    }
    iframe { border: none !important; display: block !important; }
    </style>
    """, unsafe_allow_html=True)

    # Detecta se houve erro de login para passar ao HTML
    login_error = st.session_state.get("login_error", False)
    error_html = ""
    if login_error:
        error_html = """
        <div style="background:rgba(200,30,30,0.16);border:1px solid rgba(200,30,30,0.38);
                    border-radius:10px;padding:11px 16px;font-size:13px;color:#f08080;
                    margin-bottom:16px;display:flex;align-items:center;gap:8px;">
            <span>⚠</span><span>Usuário ou senha incorretos. Tente novamente.</span>
        </div>"""

    # HTML completo da tela de login — tudo num único bloco autocontido
    login_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  html, body {{
    width: 100%; height: 100%;
    background:
      radial-gradient(ellipse 80% 60% at 75% 5%,  #4a0c10 0%, transparent 60%),
      radial-gradient(ellipse 60% 50% at 20% 90%, #2a0608 0%, transparent 55%),
      #0e0102;
    font-family: 'DM Sans', sans-serif;
    overflow: hidden;
  }}

  .screen {{
    width: 100%; height: 100vh;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 24px 16px; gap: 0;
  }}

  /* ── CABEÇALHO ── */
  .header {{ text-align: center; margin-bottom: 24px; }}

  .badge {{
    display: inline-block;
    border: 1px solid rgba(200,60,60,0.55);
    border-radius: 20px; padding: 5px 18px;
    font-size: 10px; letter-spacing: 2.5px;
    color: #c84040; text-transform: uppercase;
    font-weight: 600; margin-bottom: 14px;
  }}

  .logo {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 52px; letter-spacing: 6px;
    color: #fff; line-height: 1.0;
    text-shadow: 0 2px 20px rgba(180,20,20,0.4);
  }}
  .logo span {{ color: #d43030; }}

  .tagline {{
    font-size: 13px; color: rgba(255,255,255,0.35);
    letter-spacing: 0.5px; margin-top: 8px; font-weight: 400;
  }}

  /* ── CARD ── */
  .card {{
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px;
    padding: 32px 30px 28px 30px;
    width: 100%; max-width: 420px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 40px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.05) inset;
  }}

  .card-title {{
    font-size: 22px; font-weight: 700; color: #fff;
    margin-bottom: 4px; letter-spacing: -0.2px;
  }}
  .card-sub {{
    font-size: 13px; color: rgba(255,255,255,0.38);
    margin-bottom: 24px; font-weight: 400;
  }}

  /* ── CAMPOS ── */
  .field {{ margin-bottom: 16px; }}

  .field label {{
    display: block; font-size: 10px; letter-spacing: 2px;
    color: rgba(255,255,255,0.38); text-transform: uppercase;
    font-weight: 600; margin-bottom: 7px;
  }}

  .input-wrap {{ position: relative; }}

  .input-wrap .icon {{
    position: absolute; left: 16px; top: 50%;
    transform: translateY(-50%);
    width: 18px; height: 18px; opacity: 0.45; pointer-events: none;
  }}

  .input-wrap input {{
    width: 100%; height: 52px;
    background: rgba(0,0,0,0.40);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px; color: #fff;
    font-family: 'DM Sans', sans-serif; font-size: 15px;
    padding: 0 48px 0 46px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }}
  .input-wrap input::placeholder {{ color: rgba(255,255,255,0.22); }}
  .input-wrap input:focus {{
    border-color: rgba(212,48,48,0.55);
    box-shadow: 0 0 0 3px rgba(212,48,48,0.12);
  }}

  /* Olho (toggle senha) */
  .eye-btn {{
    position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
    background: none; border: none; cursor: pointer; padding: 4px;
    color: rgba(255,255,255,0.35); line-height: 0;
    transition: color 0.15s;
  }}
  .eye-btn:hover {{ color: rgba(255,255,255,0.65); }}

  /* ── BOTÃO ENTRAR ── */
  .btn-login {{
    width: 100%; height: 52px; margin-top: 8px;
    background: linear-gradient(135deg, #c8282a 0%, #8f1214 100%);
    border: none; border-radius: 12px; color: #fff;
    font-family: 'DM Sans', sans-serif; font-size: 15px; font-weight: 600;
    letter-spacing: 0.4px; cursor: pointer;
    box-shadow: 0 4px 24px rgba(180,20,20,0.35);
    display: flex; align-items: center; justify-content: center; gap: 8px;
    transition: opacity 0.18s, transform 0.12s;
  }}
  .btn-login:hover {{ opacity: 0.90; transform: translateY(-1px); }}
  .btn-login:active {{ opacity: 0.80; transform: translateY(0); }}
  .btn-login:disabled {{ opacity: 0.65; cursor: not-allowed; transform: none; }}

  /* Spinner */
  .spinner {{
    width: 18px; height: 18px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff; border-radius: 50%;
    animation: spin 0.7s linear infinite; display: none;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .loading .spinner {{ display: block; }}
  .loading .btn-text {{ display: none; }}

  /* ── DIVISOR ── */
  .divider {{
    display: flex; align-items: center; gap: 12px; margin: 22px 0 14px;
  }}
  .divider-line {{ flex: 1; height: 1px; background: rgba(255,255,255,0.07); }}
  .divider-text {{
    font-size: 10px; color: rgba(255,255,255,0.22);
    letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600;
  }}

  /* ── RODAPÉ ── */
  .footer-text {{
    font-size: 12px; color: rgba(255,255,255,0.25);
    text-align: center; line-height: 1.8;
  }}
  .footer-text span {{ color: #d43030; font-weight: 600; }}
</style>
</head>
<body>
<div class="screen">

  <!-- CABEÇALHO -->
  <div class="header">
    <div class="badge">Inteligência de Mercado</div>
    <div class="logo">FARMA<span>ZZ</span>INI</div>
    <div class="tagline">Intel — Análise Competitiva em Tempo Real</div>
  </div>

  <!-- CARD -->
  <div class="card">
    <div class="card-title">Bem-vindo de volta 👋</div>
    <div class="card-sub">Faça login para acessar o painel de inteligência.</div>

    {error_html}

    <!-- CAMPO USUÁRIO -->
    <div class="field">
      <label>Usuário</label>
      <div class="input-wrap">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z
               M4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75
               c-2.676 0-5.216-.584-7.499-1.632Z"/>
        </svg>
        <input id="inp-user" type="text" placeholder="Pedro Mazzini" autocomplete="username">
      </div>
    </div>

    <!-- CAMPO SENHA -->
    <div class="field">
      <label>Senha</label>
      <div class="input-wrap">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8">
          <rect x="3" y="11" width="18" height="11" rx="2"
            stroke-linecap="round" stroke-linejoin="round"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <input id="inp-pass" type="password" placeholder="••••••" autocomplete="current-password">
        <button class="eye-btn" type="button" onclick="togglePass(this)" tabindex="-1">
          <svg id="eye-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M2.036 12.322a1.012 1.012 0 0 1 0-.639
                 C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178
                 .07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5
                 c-4.638 0-8.573-3.007-9.964-7.178Z"/>
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- BOTÃO -->
    <button class="btn-login" id="btn-login" onclick="doLogin()">
      <div class="spinner"></div>
      <span class="btn-text">→&nbsp; Entrar no painel</span>
    </button>

    <!-- DIVISOR -->
    <div class="divider">
      <div class="divider-line"></div>
      <span class="divider-text">acesso restrito</span>
      <div class="divider-line"></div>
    </div>

    <!-- RODAPÉ -->
    <div class="footer-text">
      Plataforma exclusiva para a rede <span>Farmazzini</span>.<br>
      Em caso de dúvidas, contacte o administrador do sistema.
    </div>
  </div>

</div>

<script>
  // Toggle visibilidade da senha
  function togglePass(btn) {{
    const inp = document.getElementById('inp-pass');
    const isHidden = inp.type === 'password';
    inp.type = isHidden ? 'text' : 'password';
    btn.style.color = isHidden ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.35)';
  }}

  // Submete credenciais via query params → Streamlit rerun
  function doLogin() {{
    const user = document.getElementById('inp-user').value.trim();
    const pass = document.getElementById('inp-pass').value;
    if (!user || !pass) return;

    const btn = document.getElementById('btn-login');
    btn.disabled = true;
    btn.classList.add('loading');

    // Envia para o Streamlit via query params (mesmo mecanismo do chatbot)
    const params = new URLSearchParams({{
      action: 'login',
      u: user,
      p: pass
    }});
    window.parent.location.search = '?' + params.toString();
  }}

  // Enter no campo de senha dispara o login
  document.getElementById('inp-pass').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') doLogin();
  }});
  document.getElementById('inp-user').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') document.getElementById('inp-pass').focus();
  }});
</script>
</body>
</html>
"""

    # Lê os query params para autenticação (enviados pelo JS acima)
    _p = st.query_params
    if _p.get("action") == "login":
        u = _p.get("u", "")
        p = _p.get("p", "")
        st.query_params.clear()
        if u == VALID_USER and p == VALID_PASS:
            st.session_state.authenticated = True
            st.session_state.login_error   = False
            st.rerun()
        else:
            st.session_state.login_error = True
            st.rerun()

    # Renderiza o HTML como iframe fullscreen
    st.markdown("""
    <style>
    iframe { position:fixed !important; top:0 !important; left:0 !important;
             width:100vw !important; height:100vh !important;
             border:none !important; z-index:9999 !important; }
    </style>""", unsafe_allow_html=True)
    components.html(login_html, height=900, scrolling=False)


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
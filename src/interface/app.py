"""
╔══════════════════════════════════════════════════════════════════╗
║           FARMAZZINI INTEL — APP PRINCIPAL (STREAMLIT)          ║
║              VERSÃO ULTRA-FLUIDA COM TRÊS PONTOS DE LOADING      ║
║                                                                  ║
║  PROBLEMA RESOLVIDO:                                             ║
║  O processamento na AWS demorava e deixava o iframe em ecrã      ║
║  preto ou travado devido à latência de rede em navegação direta. ║
║                                                                  ║
║  SOLUÇÃO DE FLUIDEZ MÁXIMA COM TEMPO MÍNIMO DE TRANSIÇÃO:        ║
║  1. A ação "send" guarda a pergunta e adiciona um balão de       ║
║     loading com a animação clássica de 3 pontos (dot-flashing).  ║
║  2. O Streamlit limpa a URL e atualiza o iframe em milissegundos.║
║  3. O renderizador HTML (components.html) é executado PRIMEIRO.  ║
║     Isto garante que o utilizador veja a animação de carregamento║
║     a pulsar imediatamente no ecrã, sem congelar ou escurecer.   ║
║  4. No segundo plano (após renderização), o script processa      ║
║     a AWS, respeita um tempo mínimo de exibição de 3.5s para     ║
║     cobrir completamente a transição e substitui a mensagem de   ║
║     carregamento de forma limpa e suave.                         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import time  # Adicionado para medir e garantir o tempo mínimo de transição
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
# TELA DE LOGIN
# ─────────────────────────────────────────────
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { padding: 0 !important; }
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }
        footer { display: none !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"],
        .main, .block-container, .stApp {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
            overflow: hidden !important;
            height: 100dvh !important;
            min-height: unset !important;
        }
    </style>
    """, unsafe_allow_html=True)

    LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
:root {
    --primary:      #E8253A;
    --primary-mid:  #B01030;
    --primary-dark: #6B0018;
    --primary-deep: #3A000C;
    --text-main:    #ffffff;
    --text-muted:   #9a9a9f;
    --border:       rgba(255,255,255,0.06);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
    font-family: 'Urbanist', sans-serif;
    background:
        radial-gradient(ellipse 120% 80% at 50% -10%, rgba(180,20,45,0.38) 0%, rgba(80,0,18,0.20) 40%, transparent 70%),
        radial-gradient(ellipse 80% 60% at 85% 90%, rgba(120,0,25,0.28) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 10% 80%, rgba(160,15,35,0.18) 0%, transparent 55%),
        #08030A;
    color: var(--text-main);
    height: 100dvh;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Glows animados — idênticos ao chatbot */
.glow-1 {
    position: fixed; top: -20%; left: 15%; width: 70vw; height: 70vw;
    background: radial-gradient(ellipse at center, rgba(220,30,55,0.30) 0%, rgba(140,5,30,0.18) 35%, rgba(80,0,15,0.08) 60%, transparent 80%);
    filter: blur(90px); z-index: 0; pointer-events: none; border-radius: 50%;
    animation: drift1 12s ease-in-out infinite alternate;
}
.glow-2 {
    position: fixed; bottom: -15%; right: 5%; width: 55vw; height: 55vw;
    background: radial-gradient(ellipse at center, rgba(160,10,35,0.22) 0%, rgba(90,0,20,0.12) 40%, transparent 70%);
    filter: blur(110px); z-index: 0; pointer-events: none; border-radius: 50%;
    animation: drift2 15s ease-in-out infinite alternate;
}
.glow-3 {
    position: fixed; top: 40%; left: -10%; width: 40vw; height: 40vw;
    background: radial-gradient(ellipse at center, rgba(180,20,45,0.15) 0%, rgba(100,0,20,0.06) 50%, transparent 75%);
    filter: blur(80px); z-index: 0; pointer-events: none; border-radius: 50%;
    animation: drift3 18s ease-in-out infinite alternate;
}
@keyframes drift1 { from{transform:translate(0,0) scale(1)} to{transform:translate(3vw,2vh) scale(1.08)} }
@keyframes drift2 { from{transform:translate(0,0) scale(1)} to{transform:translate(-2vw,-3vh) scale(1.05)} }
@keyframes drift3 { from{transform:translate(0,0) scale(1)} to{transform:translate(4vw,-2vh) scale(1.1)} }

/* Card de login */
.login-wrapper {
    position: relative; z-index: 2;
    display: flex; flex-direction: column; align-items: center;
    gap: 36px;
    animation: cardIn 0.6s cubic-bezier(0.16,1,0.3,1) both;
}
@keyframes cardIn {
    from { opacity: 0; transform: translateY(28px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0)    scale(1);    }
}

.login-brand {
    display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.brand-pill {
    background: rgba(232,37,58,0.12);
    border: 1px solid rgba(232,37,58,0.25);
    border-radius: 100px;
    padding: 6px 16px;
    font-size: 11px; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase; color: var(--primary);
}
.brand-logo {
    font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #fff;
    line-height: 1;
}
.brand-logo span { color: var(--primary); }
.brand-sub {
    font-size: 13px; color: var(--text-muted); font-weight: 500; letter-spacing: 0.5px;
}

.login-card {
    background: rgba(10,3,14,0.92);
    border: 1px solid rgba(200,30,55,0.12);
    border-radius: 28px;
    padding: 40px 44px;
    width: 420px;
    backdrop-filter: blur(40px);
    box-shadow:
        0 32px 80px rgba(0,0,0,0.75),
        0 0 0 1px rgba(255,255,255,0.03),
        0 0 80px rgba(160,10,30,0.10);
    display: flex; flex-direction: column; gap: 28px;
}

.card-heading {
    display: flex; flex-direction: column; gap: 6px;
}
.card-title {
    font-size: 22px; font-weight: 700; color: #fff; letter-spacing: 0.3px;
}
.card-desc {
    font-size: 14px; color: var(--text-muted); font-weight: 400;
}

.fields { display: flex; flex-direction: column; gap: 16px; }

.field-group { display: flex; flex-direction: column; gap: 8px; }
.field-label {
    font-size: 12px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: var(--text-muted);
}
.field-wrap {
    position: relative;
}
.field-icon {
    position: absolute; left: 16px; top: 50%; transform: translateY(-50%);
    color: var(--text-muted); font-size: 14px; pointer-events: none;
    transition: color 0.2s;
}
.field-wrap:focus-within .field-icon { color: var(--primary); }

.field-input {
    width: 100%; height: 52px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 0 16px 0 46px;
    color: #fff;
    font-family: 'Urbanist', sans-serif;
    font-size: 15px; font-weight: 500;
    outline: none;
    transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;
}
.field-input::placeholder { color: rgba(154,154,159,0.5); }
.field-input:focus {
    border-color: rgba(232,37,58,0.45);
    background: rgba(232,37,58,0.04);
    box-shadow: 0 0 0 3px rgba(232,37,58,0.08);
}
.field-input.error {
    border-color: rgba(232,37,58,0.7) !important;
    box-shadow: 0 0 0 3px rgba(232,37,58,0.15) !important;
}

/* Toggle senha */
.toggle-pw {
    position: absolute; right: 16px; top: 50%; transform: translateY(-50%);
    color: var(--text-muted); cursor: pointer; font-size: 15px;
    transition: color 0.2s; background: none; border: none; padding: 0;
}
.toggle-pw:hover { color: var(--primary); }

/* Erro */
.error-box {
    background: rgba(232,37,58,0.10);
    border: 1px solid rgba(232,37,58,0.30);
    border-radius: 12px;
    padding: 12px 16px;
    display: none; align-items: center; gap: 10px;
    font-size: 14px; font-weight: 500; color: #ff6b7a;
}
.error-box.visible { display: flex; animation: shake 0.35s ease; }
@keyframes shake {
    0%,100%{transform:translateX(0)}
    20%{transform:translateX(-6px)}
    40%{transform:translateX(6px)}
    60%{transform:translateX(-4px)}
    80%{transform:translateX(4px)}
}

/* Botão */
.btn-login {
    height: 54px; width: 100%;
    background: linear-gradient(135deg, #E8253A 0%, #C01535 40%, #8B0828 100%);
    border: 1px solid rgba(255,80,100,0.20);
    border-radius: 16px;
    color: #fff;
    font-family: 'Urbanist', sans-serif;
    font-size: 16px; font-weight: 700; letter-spacing: 0.5px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center; gap: 10px;
    box-shadow:
        0 8px 28px rgba(200,20,50,0.40),
        0 2px 8px rgba(230,40,60,0.25),
        inset 0 1px 0 rgba(255,120,140,0.18);
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
    position: relative; overflow: hidden;
}
.btn-login::before {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 60%);
    opacity: 0; transition: opacity 0.2s;
}
.btn-login:hover::before { opacity: 1; }
.btn-login:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 36px rgba(200,20,50,0.55), 0 4px 12px rgba(230,40,60,0.30), inset 0 1px 0 rgba(255,120,140,0.20);
}
.btn-login:active { transform: translateY(0); }
.btn-login.loading { pointer-events: none; opacity: 0.8; }

/* Spinner no botão */
.btn-spinner {
    display: none; width: 18px; height: 18px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff; border-radius: 50%;
    animation: spin 0.6s linear infinite;
}
.btn-login.loading .btn-spinner { display: block; }
.btn-login.loading .btn-text { opacity: 0.7; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Divisor */
.divider {
    display: flex; align-items: center; gap: 12px;
    font-size: 12px; color: rgba(154,154,159,0.4); font-weight: 600;
}
.divider::before, .divider::after {
    content: ''; flex: 1; height: 1px;
    background: rgba(255,255,255,0.06);
}

/* Rodapé do card */
.card-footer {
    text-align: center;
    font-size: 12px; color: rgba(154,154,159,0.5);
    line-height: 1.6;
}
.card-footer strong { color: rgba(232,37,58,0.7); }
</style>
</head>
<body>
<div class="glow-1"></div>
<div class="glow-2"></div>
<div class="glow-3"></div>

<div class="login-wrapper">

    <div class="login-brand">
        <div class="brand-pill">Inteligência de Mercado</div>
        <div class="brand-logo">FARM<span>A</span>ZZINI</div>
        <div class="brand-sub">Intel &mdash; Análise Competitiva em Tempo Real</div>
    </div>

    <div class="login-card">
        <div class="card-heading">
            <div class="card-title">Bem-vindo de volta 👋</div>
            <div class="card-desc">Faça login para acessar o painel de inteligência.</div>
        </div>

        <div class="fields">
            <div class="field-group">
                <div class="field-label">Usuário</div>
                <div class="field-wrap">
                    <i class="fa-regular fa-user field-icon"></i>
                    <input id="inp-user" class="field-input" type="text"
                           placeholder="Seu nome de usuário"
                           autocomplete="username" spellcheck="false" />
                </div>
            </div>

            <div class="field-group">
                <div class="field-label">Senha</div>
                <div class="field-wrap">
                    <i class="fa-solid fa-lock field-icon"></i>
                    <input id="inp-pass" class="field-input" type="password"
                           placeholder="Sua senha de acesso"
                           autocomplete="current-password" />
                    <button class="toggle-pw" id="btn-toggle-pw" tabindex="-1" type="button">
                        <i class="fa-regular fa-eye" id="eye-icon"></i>
                    </button>
                </div>
            </div>
        </div>

        <div class="error-box" id="error-box">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span id="error-msg">Usuário ou senha inválidos.</span>
        </div>

        <button class="btn-login" id="btn-login" onclick="tentarLogin()">
            <div class="btn-spinner"></div>
            <span class="btn-text"><i class="fa-solid fa-arrow-right-to-bracket"></i>&nbsp;&nbsp;Entrar no painel</span>
        </button>

        <div class="divider">acesso restrito</div>

        <div class="card-footer">
            Plataforma exclusiva para a rede <strong>Farmazzini</strong>.<br>
            Em caso de dúvidas, contacte o administrador do sistema.
        </div>
    </div>

</div>

<script>
// ── Toggle visibilidade da senha ──────────────────────────────
document.getElementById('btn-toggle-pw').addEventListener('click', function() {
    const inp  = document.getElementById('inp-pass');
    const icon = document.getElementById('eye-icon');
    if (inp.type === 'password') {
        inp.type = 'text';
        icon.className = 'fa-regular fa-eye-slash';
    } else {
        inp.type = 'password';
        icon.className = 'fa-regular fa-eye';
    }
});

// ── Enter nos campos ──────────────────────────────────────────
document.getElementById('inp-user').addEventListener('keydown', e => { if (e.key === 'Enter') tentarLogin(); });
document.getElementById('inp-pass').addEventListener('keydown', e => { if (e.key === 'Enter') tentarLogin(); });

// ── Limpa erro ao digitar ─────────────────────────────────────
['inp-user','inp-pass'].forEach(id => {
    document.getElementById(id).addEventListener('input', () => {
        document.getElementById('error-box').classList.remove('visible');
        document.getElementById('inp-user').classList.remove('error');
        document.getElementById('inp-pass').classList.remove('error');
    });
});

// ── Lógica de login ───────────────────────────────────────────
function tentarLogin() {
    const user = document.getElementById('inp-user').value.trim();
    const pass = document.getElementById('inp-pass').value;
    const btn  = document.getElementById('btn-login');

    if (!user || !pass) {
        mostrarErro('Preencha o usuário e a senha.');
        if (!user) document.getElementById('inp-user').classList.add('error');
        if (!pass) document.getElementById('inp-pass').classList.add('error');
        return;
    }

    btn.classList.add('loading');

    // Envia as credenciais ao Streamlit via query params
    setTimeout(() => {
        const params = new URLSearchParams(window.location.search);
        const base   = window.location.pathname;
        window.parent.location.href = base + '?login_user=' + encodeURIComponent(user)
                                            + '&login_pass=' + encodeURIComponent(pass);
    }, 600); // pequeno delay para mostrar o spinner
}

function mostrarErro(msg) {
    const box = document.getElementById('error-box');
    document.getElementById('error-msg').textContent = msg;
    box.classList.remove('visible');
    void box.offsetWidth; // força reflow para reiniciar animação
    box.classList.add('visible');
}
</script>
</body>
</html>"""

    # Verifica se vieram credenciais via query params
    qp = st.query_params
    if "login_user" in qp and "login_pass" in qp:
        usuario_tentativa = qp.get("login_user", "")
        senha_tentativa   = qp.get("login_pass", "")
        st.query_params.clear()

        if USUARIOS_VALIDOS.get(usuario_tentativa) == senha_tentativa:
            st.session_state.autenticado = True
            st.session_state.usuario_logado = usuario_tentativa
            st.rerun()
        else:
            # Credenciais erradas — exibe a tela de login novamente com o iframe
            st.markdown("""
            <style>
                iframe { display:block!important; border:none!important;
                         width:100vw!important; height:100dvh!important;
                         margin:0!important; padding:0!important;
                         position:fixed!important; top:0!important; left:0!important; }
            </style>
            """, unsafe_allow_html=True)
            components.html(LOGIN_HTML, height=10000, scrolling=False)
            st.stop()
    else:
        st.markdown("""
        <style>
            iframe { display:block!important; border:none!important;
                     width:100vw!important; height:100dvh!important;
                     margin:0!important; padding:0!important;
                     position:fixed!important; top:0!important; left:0!important; }
        </style>
        """, unsafe_allow_html=True)
        components.html(LOGIN_HTML, height=10000, scrolling=False)
        st.stop()

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
# CORREÇÃO: restaura o estado completo dos chats enviado pelo frontend
# via query param 'state' (JSON serializado pelo JavaScript antes do redirect).
# Isso garante que chats criados localmente no JS (newChat, rename, etc.)
# sobrevivam ao recarregamento do Streamlit.
_params_init = st.query_params
if "state" in _params_init:
    try:
        _state = json.loads(_params_init.get("state"))
        st.session_state.chats         = _state.get("chats",         st.session_state.get("chats", []))
        st.session_state.active_chat_id = _state.get("active_chat_id", st.session_state.get("active_chat_id", 1))
        st.session_state.active_db      = _state.get("active_db",      st.session_state.get("active_db", "todas"))
        st.session_state.next_id        = _state.get("next_id",        st.session_state.get("next_id", 2))
    except (json.JSONDecodeError, Exception):
        pass  # fallback para os valores padrão abaixo

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
                # Evita duplicar mensagem se o Streamlit re-renderizar
                # sem reprocessar (ex: hot reload em desenvolvimento)
                ultima = chat["messages"][-1] if chat["messages"] else {}
                ja_tem = (ultima.get("sender") == "user" and ultima.get("text") == user_msg)

                if not ja_tem:
                    # 1. Adiciona a mensagem do utilizador instantaneamente
                    chat["messages"].append({"sender": "user", "text": user_msg})

                    if chat["title"].startswith("Nova Consulta"):
                        chat["title"] = (user_msg[:20] + "...") if len(user_msg) > 20 else user_msg

                    # 2. ADICIONA OS 3 PONTOS DE CARREGAMENTO IMEDIATAMENTE (dot-flashing)
                    # Não executa a query pesada aqui para manter o ecrã instantâneo
                    loading_html = """
                    <div class="loading-container" style="display: flex; align-items: center; padding: 12px 18px; min-height: 40px;">
                        <div class="dot-flashing"></div>
                    </div>
                    """
                    chat["messages"].append({
                        "sender": "bot",
                        "text": loading_html,
                        "is_loading": True,       # Flag para identificar o processamento pendente
                        "raw_query": user_msg,    # Guarda a pergunta para usar na AWS no ciclo seguinte
                        "saved_db": db_filter     # Guarda o filtro de base de dados correspondente
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
# RENDERIZAR HTML (PRIMEIRO PASSO)
# ─────────────────────────────────────────────
# Ao renderizar o HTML antes de iniciar a query lenta no segundo plano,
# o navegador recebe e desenha imediatamente a animação de loading no chat.
# Isto impede que o iframe fique escuro ou congelado durante o tempo de resposta da AWS.
from ui import render_full_ui

html_content = render_full_ui(
    chats=chats_json,
    active_chat_id=active_chat_id,
    active_db=active_db,
    next_id=next_id,
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

# Desenha o iframe no ecrã contendo o estado atual (pergunta e o loading animado dos 3 pontos)
components.html(html_content, height=10000, scrolling=False)

# ─────────────────────────────────────────────
# SEGUNDO PLANO: PROCESSAR PIPELINE PESADO DA AWS (SEGUNDO PASSO)
# ─────────────────────────────────────────────
# Com o HTML enviado ao cliente, o script continua a executar silenciosamente.
# Se detetar que a última mensagem requer processamento pesado, corre o pipeline 
# da AWS em background sem prejudicar a responsividade visual do iframe ativo.
chat_atual = next(
    (c for c in st.session_state.chats if c["id"] == st.session_state.active_chat_id),
    None
)

if chat_atual and chat_atual["messages"]:
    ultima_msg = chat_atual["messages"][-1]

    if ultima_msg.get("is_loading") is True:
        # Registamos o início do processamento para controlar o tempo mínimo de visualização
        start_time = time.time()

        # Recupera as informações do estado pendente
        query_pendente = ultima_msg.get("raw_query")
        db_pendente = ultima_msg.get("saved_db", "todas")

        # Corre o processamento da AWS em segundo plano estável, sem bloquear a exibição do ecrã
        resposta = processar_mensagem(
            mensagem=query_pendente,
            db_filter=db_pendente,
            historico=chat_atual["messages"][:-1]  # Envia o histórico sem o bloco temporário de loading
        )

        # Calculamos o tempo decorrido e estendemos para pelo menos 3.5 segundos de exibição fluida.
        # Isto garante que o utilizador veja os 3 pontos pulsarem e oculta qualquer tela preta de recarregamento!
        tempo_minimo = 3.5
        tempo_decorrido = time.time() - start_time
        if tempo_decorrido < tempo_minimo:
            time.sleep(tempo_minimo - tempo_decorrido)

        bot_text = f"""
            {resposta}
        """
        
        # Substitui o bloco de carregamento temporário de 3 pontos pelo HTML final com os botões de ação
        chat_atual["messages"][-1] = {"sender": "bot", "text": bot_text}
        
        # Desmarca a flag para que o próximo ciclo não re-execute o bloco de processamento
        if "is_loading" in chat_atual["messages"][-1]:
            del chat_atual["messages"][-1]["is_loading"]

        # Força uma atualização limpa para exibir o resultado final de forma instantânea
        st.rerun()
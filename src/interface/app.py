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
# ==============================================================================
# components/sidebar.py — Gerenciador Lateral de Filtros e Histórico de Consultas
# Design fiel ao HTML sandbox (dark premium, pills)
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
import time
from utils.config import FARMACIAS_VALIDAS

def render_sidebar() -> tuple[str, str]:
    """
    Renderiza a barra lateral e retorna (db_key, chat_id_ativo).
    Garante a persistência e chaveamento correto dos chats em tempo de execução.
    """
    with st.sidebar:
        # ── LOGO & TÍTULO PREMIUM ───────────────────────────────────────────
        st.markdown(
            """
            <div style="padding: 0.4rem 0 0.8rem 0;">
                <div class="sidebar-section-title">🕐 &nbsp; Chats &amp; Consultas</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── SELETOR DE BASE DE DADOS (FARMÁCIA) ──────────────────────────────
        st.markdown(
            """
            <div style="margin-bottom: 6px;">
                <span style="font-size: 11px; font-weight: 600; color: #7a7a85; 
                             text-transform: uppercase; letter-spacing: 1px;">
                    Base de Dados Ativa
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Utiliza a lista real exportada pelo seu config.py (FARMACIAS_VALIDAS)
        selected_db_label = st.radio(
            label="base_selector",
            options=FARMACIAS_VALIDAS,
            index=FARMACIAS_VALIDAS.index("Todas") if "Todas" in FARMACIAS_VALIDAS else 0,
            horizontal=True,
            label_visibility="collapsed",
            key="db_selector",
        )
        db_key = selected_db_label

        st.markdown(
            f"""
            <div style="font-size: 11px; color: #9a9a9f; margin-top: 4px; margin-bottom: 12px;">
                Filtrando: <strong style="color: #E63946;">{selected_db_label}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # ── BUSCA DE CONSULTAS NO HISTÓRICO ──────────────────────────────────
        search = st.text_input(
            "search",
            placeholder="🔍  Buscar chats...",
            label_visibility="collapsed",
            key="search_chats",
        )

        st.divider()

        # ── INICIALIZAÇÃO DE SEGURANÇA DO SESSION STATE ──────────────────────
        if "chats" not in st.session_state or not st.session_state.chats:
            st.session_state.chats = {
                "chat_1": {
                    "title": "Análise de Preço: Dipirona",
                    "messages": [],
                }
            }
        if "active_chat" not in st.session_state:
            st.session_state.active_chat = list(st.session_state.chats.keys())[0]

        chats = st.session_state.chats
        active = st.session_state.active_chat
        search_lower = search.lower().strip()

        # ── RENDERIZAÇÃO DO HISTÓRICO DE CHATS ────────────────────────────────
        st.markdown('<div class="sidebar-section-title" style="margin-bottom: 12px;">Histórico</div>', unsafe_allow_html=True)

        # Convertido para lista para evitar RuntimeError ao deletar chaves do dicionário em loop
        for chat_id, chat_data in list(chats.items()):
            # Filtro reativo de busca por título do chat
            if search_lower and search_lower not in chat_data.get("title", "").lower():
                continue

            is_active = (chat_id == active)
            icon = "💬" if is_active else "🗨️"
            label_botao = f"{icon} {chat_data.get('title', 'Consulta')}"

            col_btn, col_del = st.columns([5, 1])

            with col_btn:
                # Troca dinamicamente o comportamento visual baseado no chat focado pelo analista
                if st.button(
                    label_botao,
                    key=f"select_{chat_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.active_chat = chat_id
                    st.rerun()

            with col_del:
                # Impede que o usuário delete se for o único chat ativo na memória
                if len(chats) > 1:
                    if st.button("🗑", key=f"del_{chat_id}", help="Excluir consulta histórica"):
                        del st.session_state.chats[chat_id]
                        remaining = list(st.session_state.chats.keys())
                        st.session_state.active_chat = remaining[0]
                        st.rerun()

        st.divider()

        # ── BOTÃO OPERACIONAL: CRIAR NOVO CHAT ───────────────────────────────
        if st.button("＋  Novo Chat", use_container_width=True, key="new_chat_btn", type="secondary"):
            new_id = f"chat_{int(time.time())}"
            count = len(st.session_state.chats) + 1
            st.session_state.chats[new_id] = {
                "title": f"Nova Consulta #{count}",
                "messages": [],
            }
            st.session_state.active_chat = new_id
            st.rerun()

        # Footer flutuante da barra lateral
        st.markdown(
            """
            <div style="margin-top: auto; padding-top: 30px; font-size: 10px; 
                        color: rgba(255,255,255,0.12); text-align: center; letter-spacing: 1.5px;
                        font-family: 'Space Grotesk', sans-serif;">
                FARMAZZINI INTEL v2.0
            </div>
            """,
            unsafe_allow_html=True,
        )

    return db_key, st.session_state.active_chat
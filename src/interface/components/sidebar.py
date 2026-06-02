"""
Sidebar: seletor de base de dados e histórico de chats.
Design fiel ao HTML sandbox (dark premium, pills, Urbanist).
"""

import streamlit as st
from utils.config import DB_OPTIONS


def render_sidebar() -> tuple[str, str]:
    """
    Renderiza a sidebar e retorna (db_key, chat_id_ativo).
    """
    with st.sidebar:
        # ── TÍTULO ──────────────────────────────────────────────────────────
        st.markdown(
            '<div class="sidebar-title">🕐 &nbsp; Chats &amp; Consultas</div>',
            unsafe_allow_html=True,
        )

        # ── SELETOR DE BASE ──────────────────────────────────────────────────
        st.markdown(
            '<div class="db-selector-container">'
            '<div class="db-label">Base de Dados Ativa</div>',
            unsafe_allow_html=True,
        )

        selected_db_label = st.radio(
            label="base_selector",
            options=list(DB_OPTIONS.keys()),
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key="db_selector",
        )
        db_key = DB_OPTIONS[selected_db_label]

        st.markdown(
            f'<div style="font-size:11px; color:#9a9a9f; margin-top:6px;">'
            f'Filtrando: <strong style="color:#E63946;">{selected_db_label}</strong>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── BUSCA ────────────────────────────────────────────────────────────
        search = st.text_input(
            "search",
            placeholder="🔍  Buscar chats...",
            label_visibility="collapsed",
            key="search_chats",
        )

        st.divider()

        # ── INICIALIZAR ESTADO ───────────────────────────────────────────────
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

        # ── LISTA DE CHATS ────────────────────────────────────────────────────
        st.markdown('<div class="db-label" style="margin-bottom:8px;">Histórico</div>', unsafe_allow_html=True)

        for chat_id, chat_data in list(chats.items()):
            if search_lower and search_lower not in chat_data["title"].lower():
                continue

            is_active = chat_id == active
            icon = "💬" if is_active else "🗨️"
            label = f"{icon} {chat_data['title']}"

            col_btn, col_del = st.columns([5, 1])

            with col_btn:
                if st.button(
                    label,
                    key=f"select_{chat_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.active_chat = chat_id
                    st.rerun()

            with col_del:
                if len(chats) > 1:
                    if st.button("🗑", key=f"del_{chat_id}", help="Excluir"):
                        del st.session_state.chats[chat_id]
                        remaining = list(st.session_state.chats.keys())
                        st.session_state.active_chat = remaining[0]
                        st.rerun()

        st.divider()

        # ── NOVO CHAT ────────────────────────────────────────────────────────
        if st.button("＋  Novo Chat", use_container_width=True, key="new_chat_btn"):
            import time
            new_id = f"chat_{int(time.time())}"
            count = len(st.session_state.chats) + 1
            st.session_state.chats[new_id] = {
                "title": f"Nova Consulta #{count}",
                "messages": [],
            }
            st.session_state.active_chat = new_id
            st.rerun()

        st.markdown(
            '<div style="margin-top:auto; padding-top:20px; font-size:10px; '
            'color:rgba(255,255,255,0.15); text-align:center; letter-spacing:1px;">'
            'FARMAZZINI INTEL v2.0</div>',
            unsafe_allow_html=True,
        )

    return db_key, st.session_state.active_chat
# ==============================================================================
# sidebar.py — Barra lateral estilo Farmazzini Intel
# Projeto Farmazzini | Poli Júnior | Equipe 06
# Design: glassmorphism, Urbanist, #E63946
# ==============================================================================

import streamlit as st
from utils.config import FARMACIAS_VALIDAS, DEFAULT_ANO, DEFAULT_MES, DEFAULT_DIA


def render_sidebar() -> dict:
    with st.sidebar:

        # ── Logo estilo Intel ──────────────────────────────────────────────
        st.markdown("""
        <div style="padding: 1rem 0 0.5rem 0;">
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:2.5px;
                        color:#E63946; font-weight:700; margin-bottom:4px;">
                Intelligence Platform
            </div>
            <div style="font-family:'Urbanist',sans-serif; font-size:1.5rem;
                        font-weight:700; color:#ffffff; letter-spacing:3px;">
                FARMA<span style="color:#E63946;">ZZINI</span>
            </div>
            <div style="display:inline-block; margin-top:8px; padding:3px 8px;
                        background:rgba(99,102,241,0.15); border:1px solid #6366f1;
                        border-radius:4px; font-size:10px; font-weight:700;
                        color:#818cf8; text-transform:uppercase; letter-spacing:1px;">
                ✦ Claude Conectado
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Filtro de base de dados (estilo db-pills do HTML) ──────────────
        st.markdown("""
        <div style="font-size:11px; text-transform:uppercase; color:#9a9a9f;
                    font-weight:700; letter-spacing:1px; margin-bottom:8px;">
            Base de Dados Ativa
        </div>
        """, unsafe_allow_html=True)

        farmacia_selecionada = st.selectbox(
            label="Farmácia",
            options=["Todas"] + FARMACIAS_VALIDAS,
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Informações do projeto ─────────────────────────────────────────
        st.markdown("""
        <div style="font-size:11px; text-transform:uppercase; color:#E63946;
                    font-weight:700; letter-spacing:2.5px; margin-bottom:10px;">
            Projeto
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="font-size:13px; color:#9a9a9f; line-height:2;">
            <span style="color:#ffffff; font-weight:600;">Equipe</span> &nbsp;06 — Poli Júnior<br>
            <span style="color:#ffffff; font-weight:600;">Dados</span> &nbsp;{DEFAULT_DIA}/{DEFAULT_MES}/{DEFAULT_ANO}<br>
            <span style="color:#ffffff; font-weight:600;">Modelo IA</span> &nbsp;Claude Haiku 4.5<br>
            <span style="color:#ffffff; font-weight:600;">Região AWS</span> &nbsp;us-east-2 (Ohio)
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Exemplos de perguntas ──────────────────────────────────────────
        st.markdown("""
        <div style="font-size:11px; text-transform:uppercase; color:#E63946;
                    font-weight:700; letter-spacing:2.5px; margin-bottom:4px;">
            Consultas Rápidas
        </div>
        <div style="font-size:12px; color:#9a9a9f; margin-bottom:10px;">
            Clique para executar diretamente.
        </div>
        """, unsafe_allow_html=True)

        exemplos = [
            "Qual o produto mais caro da FarmaPonte?",
            "Quais itens têm cashback ativo na Vera Cruz?",
            "Liste os 10 produtos com maior desconto padrão.",
            "Compare os preços PIX entre as farmácias.",
            "Quais produtos estão indisponíveis hoje?",
        ]

        for ex in exemplos:
            if st.button(ex, key=f"ex_{ex[:25]}", use_container_width=True):
                st.session_state["exemplo_selecionado"] = ex
                st.session_state["executar_exemplo"]    = True

        st.markdown("---")

        # ── Créditos ───────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center; font-size:11px; color:#9a9a9f; padding-top:0.5rem;
                    letter-spacing:0.5px;">
            Desenvolvido com ❤️ pela<br>
            <span style="color:#ffffff; font-weight:600;">Poli Júnior</span>
            &nbsp;×&nbsp;
            <span style="color:#E63946; font-weight:600;">Farmazzini</span>
        </div>
        """, unsafe_allow_html=True)

    return {
        "farmacia": None if farmacia_selecionada == "Todas" else farmacia_selecionada,
    }
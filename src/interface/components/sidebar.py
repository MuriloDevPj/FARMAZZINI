# ==============================================================================
# sidebar.py — Componente da barra lateral
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
from utils.config import FARMACIAS_VALIDAS, DEFAULT_ANO, DEFAULT_MES, DEFAULT_DIA


def render_sidebar() -> dict:
    with st.sidebar:
        # ── Logo ───────────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
            <span style="font-family:'Syne',sans-serif; font-size:1.6rem;
                         font-weight:800; color:#FFFFFF; letter-spacing:-0.02em;">
                💊 FARMA<span style="color:#C0392B;">ZZINI</span>
            </span>
            <p style="color:#666; font-size:0.72rem; margin:0.2rem 0 0 0;
                      text-transform:uppercase; letter-spacing:0.12em;">
                Intelligence Platform
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Filtros ────────────────────────────────────────────────────────
        st.markdown("##### 🔎 Filtros Contextuais")
        st.caption("Esses filtros orientam a IA na geração do SQL.")

        farmacia_selecionada = st.selectbox(
            "Farmácia concorrente",
            options=["Todas"] + FARMACIAS_VALIDAS,
        )

        st.markdown("---")

        # ── Informações do projeto ─────────────────────────────────────────
        st.markdown("##### 📋 Projeto")
        st.markdown(f"""
        <div style="font-size:0.8rem; color:#888; line-height:1.7;">
            <b style="color:#CCC;">Equipe</b> 06 — Poli Júnior<br>
            <b style="color:#CCC;">Dados</b> {DEFAULT_DIA}/{DEFAULT_MES}/{DEFAULT_ANO}<br>
            <b style="color:#CCC;">Modelo IA</b> Claude Haiku 4.5<br>
            <b style="color:#CCC;">Região AWS</b> us-east-2 (Ohio)
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Exemplos de perguntas ──────────────────────────────────────────
        st.markdown("##### 💡 Exemplos de Perguntas")
        st.caption("Clique para executar diretamente.")

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
                st.session_state["executar_exemplo"] = True

        st.markdown("---")

        # ── Créditos ───────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center; font-size:0.7rem; color:#555; padding-top:0.5rem;">
            Desenvolvido com ❤️ pela<br>
            <b style="color:#888;">Poli Júnior</b> × <b style="color:#888;">Farmazzini</b>
        </div>
        """, unsafe_allow_html=True)

    return {
        "farmacia": None if farmacia_selecionada == "Todas" else farmacia_selecionada,
    }
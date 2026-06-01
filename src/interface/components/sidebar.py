# ==============================================================================
# sidebar.py — Sidebar Farmazzini 2.0
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
from utils.config import FARMACIAS_VALIDAS, DEFAULT_ANO, DEFAULT_MES, DEFAULT_DIA


def render_sidebar() -> dict:
    with st.sidebar:
        # ── Logo ───────────────────────────────────────────────────────────
        st.markdown("""
        <div style="padding:1rem 0 0.5rem 0;">
            <div style="font-size:1.3rem;font-weight:700;letter-spacing:3px;color:#fff;">
                FARMA<span style="color:#E63946;">ZZINI</span>
                <span style="margin-left:8px;" class="badge-red">INTEL</span>
            </div>
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:2.5px;
                        color:#E63946;font-weight:700;margin-top:6px;">
                Chats & Consultas
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Seletor de base de dados (pills) ───────────────────────────────
        st.markdown('<div class="sidebar-section-title">Base de Dados Ativa</div>',
                    unsafe_allow_html=True)

        opcoes = ["Todas", "FarmaPonte", "Vera Cruz"]
        farmacia_sel = st.radio(
            label="base",
            options=opcoes,
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Informações do modelo ──────────────────────────────────────────
        st.markdown(f"""
        <div style="font-size:0.78rem;color:#9a9a9f;line-height:1.8;">
            <b style="color:#ccc;">Dados</b> {DEFAULT_DIA}/{DEFAULT_MES}/{DEFAULT_ANO}<br>
            <b style="color:#ccc;">Modelo</b> Claude Haiku 4.5<br>
            <b style="color:#ccc;">Região</b> us-east-2 (Ohio)<br>
            <b style="color:#ccc;">Equipe</b> 06 — Poli Júnior
        </div>
        <div style="margin-top:10px;">
            <span class="badge-green">✨ Bedrock Conectado</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Atalhos rápidos ────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-title">Atalhos Rápidos</div>',
                    unsafe_allow_html=True)
        st.caption("Clique para executar diretamente.")

        atalhos = {
            "📦 Estoque Crítico": "Quais produtos estão Indisponíveis hoje nas farmácias?",
            "🏷️ Achar Mais Barato": "Qual a dipirona mais barata disponível nas farmácias?",
            "🔥 Maiores Promoções": "Liste os 10 produtos com maior desconto padrão.",
            "💊 Preço Médio": "Qual o preço médio dos produtos disponíveis por farmácia?",
            "💳 Comparar PIX": "Compare os preços PIX médios entre FarmaPonte e Vera Cruz.",
        }

        for label, pergunta in atalhos.items():
            if st.button(label, key=f"hot_{label}", use_container_width=True):
                st.session_state["exemplo_selecionado"] = pergunta
                st.session_state["executar_exemplo"] = True

        st.markdown("---")

        # ── Créditos ───────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;font-size:0.7rem;color:#444;padding-top:0.5rem;">
            Desenvolvido pela <b style="color:#666;">Poli Júnior</b><br>
            para <b style="color:#666;">Farmazzini</b> © 2026
        </div>
        """, unsafe_allow_html=True)

    return {
        "farmacia": None if farmacia_sel == "Todas" else farmacia_sel,
    }
# ==============================================================================
# sidebar.py — Sidebar Farmazzini Intel 2.0  |  Design refresh
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
from utils.config import FARMACIAS_VALIDAS, DEFAULT_ANO, DEFAULT_MES, DEFAULT_DIA


def render_sidebar() -> dict:
    with st.sidebar:

        # ── Logo ───────────────────────────────────────────────────────────────
        st.markdown("""
        <div style="padding:0.8rem 0 0.4rem;">
            <div style="font-family:'Space Grotesk',sans-serif;
                        font-size:1.2rem;font-weight:700;letter-spacing:2.5px;
                        text-transform:uppercase;color:#f0f0f2;">
                Farma<span style="color:#E63946;">zzini</span>
                <span style="margin-left:8px;" class="badge-red">Intel</span>
            </div>
            <div style="font-family:'Space Grotesk',sans-serif;
                        font-size:10px;text-transform:uppercase;letter-spacing:2.5px;
                        color:#E63946;font-weight:700;margin-top:6px;">
                Chats &amp; Consultas
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Seletor de base (pills emuladas via radio) ─────────────────────────
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

        # ── Info do modelo ──────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="font-family:'DM Sans',sans-serif;
                    font-size:0.76rem;color:#7a7a85;line-height:2;">
            <span style="color:#ccc;font-weight:600;">Dados</span>
            &nbsp;{DEFAULT_DIA}/{DEFAULT_MES}/{DEFAULT_ANO}<br>
            <span style="color:#ccc;font-weight:600;">Modelo</span>
            &nbsp;Claude Haiku 4.5<br>
            <span style="color:#ccc;font-weight:600;">Região</span>
            &nbsp;us-east-2 (Ohio)<br>
            <span style="color:#ccc;font-weight:600;">Equipe</span>
            &nbsp;06 — Poli Júnior
        </div>
        <div style="margin-top:10px;">
            <span class="badge-green">✨ Bedrock Conectado</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Atalhos rápidos ─────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-title">Atalhos Rápidos</div>',
                    unsafe_allow_html=True)
        st.caption("Clique para executar diretamente.")

        atalhos = {
            "📦 Estoque Crítico":  "Quais produtos estão Indisponíveis hoje nas farmácias?",
            "🏷️ Achar Mais Barato": "Qual o produto mais barato disponível por farmácia?",
            "🔥 Maiores Promoções": "Liste os 10 produtos com maior desconto padrão.",
            "💊 Preço Médio":       "Qual o preço médio dos produtos disponíveis por farmácia?",
            "💳 Comparar PIX":      "Compare os preços PIX médios entre FarmaPonte e Vera Cruz.",
        }

        for label, pergunta in atalhos.items():
            if st.button(label, key=f"hot_{label}", use_container_width=True):
                st.session_state["exemplo_selecionado"] = pergunta
                st.session_state["executar_exemplo"] = True

        st.markdown("---")

        # ── Créditos ────────────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;font-size:0.68rem;color:#3a3a42;padding-top:0.4rem;
                    font-family:'DM Sans',sans-serif;">
            Desenvolvido pela <b style="color:#555;">Poli Júnior</b><br>
            para <b style="color:#555;">Farmazzini</b> © 2026
        </div>
        """, unsafe_allow_html=True)

    return {
        "farmacia": None if farmacia_sel == "Todas" else farmacia_sel,
    }
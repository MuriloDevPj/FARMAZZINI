# ==============================================================================
# painel_alertas.py — Componente visual do painel de alertas comerciais
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
from utils.alertas import buscar_alertas_comerciais


def render_painel_alertas():
    """
    Renderiza o painel de alertas comerciais na página principal.
    Carrega os alertas uma vez por sessão (cache em session_state).
    """
    # Cache por sessão para não reexecutar a query a cada rerun
    if "alertas_comerciais" not in st.session_state:
        with st.spinner("🔍 Verificando alertas de mercado..."):
            st.session_state["alertas_comerciais"] = buscar_alertas_comerciais()

    alertas = st.session_state["alertas_comerciais"]

    if not alertas:
        st.info("✅ Nenhuma anomalia de preço detectada nas últimas 48 horas.")
        return

    st.markdown(f"### 🚨 Alertas Comerciais — {len(alertas)} anomalia(s) detectada(s)")

    for alerta in alertas:
        with st.container():
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #2E0D0D, #1A0A0A);
                border: 1px solid #8B1A1A;
                border-left: 4px solid #C0392B;
                border-radius: 10px;
                padding: 1rem 1.25rem;
                margin-bottom: 0.75rem;
            ">
                <div style="font-size:0.75rem; color:#888; text-transform:uppercase;
                            letter-spacing:0.08em; margin-bottom:0.4rem;">
                    ⚠️ Alerta Comercial · {alerta['farmacia']}
                </div>
                <div style="font-size:1rem; color:#F0F0F0; font-weight:600;">
                    {alerta['nome']}
                </div>
                <div style="font-size:0.85rem; color:#CCC; margin-top:0.3rem;">
                    Queda de <span style="color:#FF6B6B; font-weight:700;">
                    {alerta['queda_pct']:.1f}%</span> nas últimas 48h —
                    de <span style="color:#AAA;">R$ {alerta['preco_ref']:.2f}</span>
                    → <span style="color:#FF6B6B; font-weight:600;">
                    R$ {alerta['preco_concorrente']:.2f}</span>
                    {f'&nbsp;&nbsp;|&nbsp;&nbsp;EAN: <span style="color:#666;">{alerta["ean"]}</span>'
                     if alerta.get("ean") and alerta["ean"] != "—" else ""}
                </div>
                {f'<div style="font-size:0.82rem; color:#F5A623; margin-top:0.4rem;">⚡ Seu preço está R$ {alerta["diferenca_reais"]:.2f} acima deles.</div>'
                 if alerta.get("diferenca_reais") else ""}
            </div>
            """, unsafe_allow_html=True)

    # Botão para recarregar alertas manualmente
    if st.button("🔄 Atualizar alertas", key="btn_atualizar_alertas"):
        del st.session_state["alertas_comerciais"]
        st.rerun()
"""
Componente de métricas e tabela de dados da Farmazzini.
Exibe KPIs de estoque e comparativo de preços em formato executivo.
"""

import streamlit as st
import pandas as pd
from utils.config import PRODUCTS_DB


def render_metrics_bar():
    """
    Renderiza 4 KPI cards horizontais com status rápido do estoque.
    """
    cols = st.columns(4)

    kpis = [
        {
            "label": "Itens Monitorados",
            "value": str(len(PRODUCTS_DB)),
            "delta": "base ativa",
        },
        {
            "label": "Estoque Crítico",
            "value": str(sum(1 for p in PRODUCTS_DB if p["estoque"] <= 4)),
            "delta": "requer reposição",
            "delta_color": "inverse",
        },
        {
            "label": "Menor Preço Mercado",
            "value": "R$ 8,94",
            "delta": "Vera Cruz PIX",
        },
        {
            "label": "Concorrentes Ativos",
            "value": "2",
            "delta": "FarmaPonte + Vera Cruz",
        },
    ]

    for col, kpi in zip(cols, kpis):
        with col:
            st.metric(
                label=kpi["label"],
                value=kpi["value"],
                delta=kpi["delta"],
                delta_color=kpi.get("delta_color", "normal"),
            )


def render_price_table(db_filter: str = "todas"):
    """
    Exibe tabela comparativa de preços filtrada pelo concorrente selecionado.
    
    Args:
        db_filter: 'todas' | 'ponte' | 'veracruz'
    """
    rows = []

    for p in PRODUCTS_DB:
        row = {
            "Produto": p["name"],
            "Estoque": f"{p['estoque']} un  {p['status']}",
            "Farmazzini": f"R$ {p['farmazzini']:.2f}",
        }

        if db_filter in ("todas", "ponte"):
            row["FarmaPonte"] = f"R$ {p['farmaponte']:.2f}"
            row["Promo Ponte"] = p["farmaponte_promo"]

        if db_filter in ("todas", "veracruz"):
            row["Vera Cruz"] = f"R$ {p['veracruz']:.2f}"
            if p["veracruz_pix"]:
                row["Vera Cruz PIX"] = f"R$ {p['veracruz_pix']:.2f}"
            row["Promo Vera Cruz"] = p["veracruz_promo"]

        rows.append(row)

    df = pd.DataFrame(rows)

    st.markdown(
        """
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px;
                    color:#E63946; font-weight:700; margin-bottom:8px;">
            📊 Comparativo de Preços — Mercado Regional
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    # ── EXPORT CSV ──────────────────────────────────────────────────────────
    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Exportar CSV",
        data=csv_data,
        file_name="farmazzini_precos.csv",
        mime="text/csv",
        key="download_csv_table",
    )


def render_stock_chart():
    """
    Renderiza gráfico de barras de estoque usando st.bar_chart nativo.
    """
    import pandas as pd

    data = {p["name"].split(" ")[0]: p["estoque"] for p in PRODUCTS_DB}
    df = pd.DataFrame.from_dict(data, orient="index", columns=["Estoque (un)"])

    st.markdown(
        """
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px;
                    color:#E63946; font-weight:700; margin: 12px 0 8px 0;">
            📦 Nível de Estoque por Produto
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.bar_chart(df, color="#E63946", height=200)
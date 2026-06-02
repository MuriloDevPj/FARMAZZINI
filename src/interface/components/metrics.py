# ==============================================================================
# components/metrics.py — Painel e Cards Analíticos de Mercado (Híbrido)
# Suporta renderização estática e dinâmica baseada nas queries do Athena/S3
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
import pandas as pd

try:
    from utils.config import PRODUCTS_DB
except ImportError:
    # Fallback estrutural seguro caso o arquivo de configuração mude de local
    PRODUCTS_DB = []


def render_metrics(df: pd.DataFrame = None, key: str = "0"):
    """
    Função unificada exigida pelo chat.py.
    Renderiza os cartões de KPIs dinamicamente com base em dados do S3 ou do PRODUCTS_DB.
    """
    if df is None or df.empty:
        # Se nenhum DataFrame for fornecido, executa o painel estático padrão
        render_metrics_bar()
        return

    st.markdown(
        """<div style='font-family:"Space Grotesk",sans-serif;
        font-size:12px; font-weight:700; text-transform:uppercase;
        letter-spacing:1.5px; color:#E63946; margin-bottom:12px;'>
        📊 Resultado Consolidados da Análise de Mercado
        </div>""",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Registros Encontrados", f"{len(df):,}")

    with col2:
        if "preco_original" in df.columns:
            serie = pd.to_numeric(df["preco_original"], errors="coerce").dropna()
            if not serie.empty:
                st.metric("Preço Médio (Original)", f"R$ {serie.mean():,.2f}")
            else:
                st.metric("Preço Médio (Original)", "—")
        else:
            st.metric("Colunas", str(len(df.columns)))

    with col3:
        if "preco_pix" in df.columns:
            serie = pd.to_numeric(df["preco_pix"], errors="coerce").dropna()
            if not serie.empty:
                st.metric("Menor Preço (PIX)", f"R$ {serie.min():,.2f}")
            else:
                st.metric("Menor Preço (PIX)", "—")
        elif "preco_original" in df.columns:
            serie = pd.to_numeric(df["preco_original"], errors="coerce").dropna()
            st.metric("Menor Preço", f"R$ {serie.min():,.2f}" if not serie.empty else "—")
        else:
            st.metric("Linhas", str(len(df)))

    with col4:
        if "disponibilidade" in df.columns:
            disponiveis = df["disponibilidade"].str.lower().eq("disponível").sum()
            st.metric("Itens Disponíveis", f"{disponiveis:,}")
        elif "farmacia" in df.columns:
            st.metric("Farmácias", str(df["farmacia"].nunique()))
        else:
            st.metric("Status Operacional", "✅ Síncrono")


def render_metrics_bar():
    """
    KPI cards estáticos baseados no PRODUCTS_DB para o painel colapsável.
    """
    cols = st.columns(4)
    
    total_itens = len(PRODUCTS_DB)
    itens_criticos = sum(1 for p in PRODUCTS_DB if p.get("estoque", 0) <= 4)
    
    kpis = [
        {"label": "Itens Monitorados", "value": str(total_itens), "delta": "base ativa"},
        {"label": "Estoque Crítico", "value": str(itens_criticos), "delta": "requer reposição", "delta_color": "inverse"},
        {"label": "Menor Preço", "value": "R$ 8,94", "delta": "Vera Cruz PIX"},
        {"label": "Concorrentes", "value": "2", "delta": "Ponte + Vera Cruz"},
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
    Tabela comparativa de preços com botão de exportação CSV inteligente e normalização de filtros.
    """
    if not PRODUCTS_DB:
        st.info("Nenhum dado disponível no banco de dados local para exibição estática.")
        return

    # Normaliza filtros para evitar quebras por causa de maiúsculas/minúsculas vindas da interface
    filtro_limpo = str(db_filter).lower().strip()

    rows = []
    for p in PRODUCTS_DB:
        row = {
            "Produto": p.get("name", "Desconhecido"),
            "Estoque": f"{p.get('estoque', 0)} un  {p.get('status', '')}",
            "Farmazzini": f"R$ {p.get('farmazzini', 0.0):.2f}",
        }
        
        # Filtros condicionais que mapeiam "todas", "farmaponte" ou "vera cruz"
        if filtro_limpo in ("todas", "ponte", "farmaponte"):
            row["FarmaPonte"] = f"R$ {p.get('farmaponte', 0.0):.2f}"
            row["Promo Ponte"] = p.get("farmaponte_promo", "Não")
            
        if filtro_limpo in ("todas", "veracruz", "vera cruz"):
            row["Vera Cruz"] = f"R$ {p.get('veracruz', 0.0):.2f}"
            if p.get("veracruz_pix"):
                row["PIX"] = f"R$ {p.get('veracruz_pix', 0.0):.2f}"
            row["Promo Vera Cruz"] = p.get("veracruz_promo", "Não")
            
        rows.append(row)

    df = pd.DataFrame(rows)

    st.markdown(
        """<div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; 
        color:#E63946; font-weight:700; margin-bottom:8px; font-family:'Space Grotesk',sans-serif;">
        📊 Comparativo de Preços — Mercado Regional
        </div>""",
        unsafe_allow_html=True,
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Exportar Painel para CSV",
        data=csv_data,
        file_name="farmazzini_painel_precos.csv",
        mime="text/csv",
        key="download_csv_metrics_table",
        use_container_width=True
    )


def render_stock_chart():
    """
    Gráfico de barras nativo de nível de estoque.
    """
    if not PRODUCTS_DB:
        return

    # Extrai o primeiro termo do nome do medicamento para encurtar e não quebrar o design do eixo X
    data = {p["name"].split(" ")[0]: p.get("estoque", 0) for p in PRODUCTS_DB}
    df = pd.DataFrame.from_dict(data, orient="index", columns=["Estoque (un)"])
    
    st.markdown(
        """<div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; 
        color:#E63946; font-weight:700; margin:12px 0 8px 0; font-family:'Space Grotesk',sans-serif;">
        📦 Nível de Estoque por Produto
        </div>""",
        unsafe_allow_html=True,
    )
    st.bar_chart(df, color="#E63946", height=200)
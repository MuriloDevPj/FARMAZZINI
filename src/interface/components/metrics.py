# ==============================================================================
# metrics.py — Cards de métricas rápidas do mercado
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
import pandas as pd


def render_metrics(df: pd.DataFrame, key: str = "0"):
    if df is None or df.empty:
        return

    st.markdown("#### 📊 Resultado da Análise de Mercado")

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
            if not serie.empty:
                st.metric("Menor Preço", f"R$ {serie.min():,.2f}")
            else:
                st.metric("Menor Preço", "—")
        else:
            st.metric("Linhas", str(len(df)))

    with col4:
        if "disponibilidade" in df.columns:
            disponiveis = df["disponibilidade"].eq("Disponível").sum()
            st.metric("Disponíveis", f"{disponiveis:,}")
        elif "farmacia" in df.columns:
            st.metric("Farmácias", str(df["farmacia"].nunique()))
        else:
            st.metric("Status", "✅ OK")

    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Baixar resultado em CSV",
        data=csv_bytes,
        file_name="resultado_farmazzini.csv",
        mime="text/csv",
        key=f"download_{key}",
    )
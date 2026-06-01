# ==============================================================================
# metrics.py — Cards de métricas rápidas do mercado
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
import pandas as pd


def render_metrics(df: pd.DataFrame, key: str = "0"):
    """
    Exibe cards de métricas resumidas a partir do DataFrame de resultado.
    O parâmetro key deve ser único por chamada (usar o idx da mensagem).
    """
    if df is None or df.empty:
        return

    st.markdown("#### 📊 Resultado da Análise de Mercado")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Registros Encontrados", f"{len(df):,}")

    with col2:
        if "preco_original" in df.columns:
            media = pd.to_numeric(df["preco_original"], errors="coerce").mean()
            st.metric("Preço Médio (Original)", f"R$ {media:,.2f}")
        else:
            st.metric("Colunas", str(len(df.columns)))

    with col3:
        if "preco_pix" in df.columns:
            minimo = pd.to_numeric(df["preco_pix"], errors="coerce").min()
            st.metric("Menor Preço (PIX)", f"R$ {minimo:,.2f}")
        elif "preco_original" in df.columns:
            minimo = pd.to_numeric(df["preco_original"], errors="coerce").min()
            st.metric("Menor Preço", f"R$ {minimo:,.2f}")
        else:
            st.metric("Linhas", str(len(df)))

    with col4:
        if "disponibilidade" in df.columns:
            disponiveis = df["disponibilidade"].str.lower().eq("disponível").sum()
            st.metric("Disponíveis", f"{disponiveis:,}")
        elif "farmacia" in df.columns:
            n_farmacias = df["farmacia"].nunique()
            st.metric("Farmácias", str(n_farmacias))
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
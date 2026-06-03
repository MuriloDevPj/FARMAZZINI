# ==============================================================================
# pipeline.py — Orquestrador do pipeline de dados
# Projeto Farmazzini | Poli Júnior | Equipe 06
#
# Este arquivo é o único elo que faltava entre o app.py e o aws_client.py.
# O app.py chama: processar_mensagem(mensagem, db_filter, historico)
# O aws_client.py expõe: buscar_dados(pergunta, base) → dict
#
# Fluxo:
#   1. Recebe a pergunta do usuário via app.py
#   2. Chama buscar_dados() do aws_client (Bedrock → Step Functions → S3)
#   3. Formata o resultado como HTML para ser renderizado no chat
# ==============================================================================

import pandas as pd
from aws_client import buscar_dados


# ── Helpers de formatação HTML ────────────────────────────────────────────────

def _df_para_html(df: pd.DataFrame) -> str:
    """Converte um DataFrame em uma tabela HTML estilizada com o design Farmazzini."""
    colunas = list(df.columns)
    header_cells = "".join(f"<th>{col}</th>" for col in colunas)

    linhas_html = ""
    for _, row in df.iterrows():
        cells = ""
        for col in colunas:
            valor = row[col]
            # Destaca preços em vermelho
            if "preco" in col.lower() and pd.notna(valor):
                try:
                    cells += f'<td style="color:#E8253A;font-weight:600;">R$ {float(valor):,.2f}</td>'
                    continue
                except (ValueError, TypeError):
                    pass
            # Destaca disponibilidade
            if col.lower() == "disponibilidade":
                cor = "#4ade80" if str(valor) == "Disponível" else "#f87171"
                cells += f'<td style="color:{cor};font-weight:600;">{valor}</td>'
                continue
            cells += f"<td>{valor if pd.notna(valor) else '—'}</td>"
        linhas_html += f"<tr>{cells}</tr>"

    return f"""
    <div style="overflow-x:auto;margin-top:16px;border-radius:12px;border:1px solid rgba(255,255,255,0.06);">
        <table style="width:100%;border-collapse:collapse;font-size:13px;font-family:'Urbanist',sans-serif;">
            <thead>
                <tr style="background:rgba(232,37,58,0.12);color:#E8253A;text-transform:uppercase;
                           font-size:11px;letter-spacing:1px;">
                    {header_cells}
                </tr>
            </thead>
            <tbody style="color:#ffffff;">
                {linhas_html}
            </tbody>
        </table>
    </div>
    <p style="color:#9a9a9f;font-size:12px;margin-top:8px;">
        {len(df):,} registro(s) encontrado(s)
    </p>
    """


def _metricas_rapidas(df: pd.DataFrame) -> str:
    """Gera cards de métricas rápidas acima da tabela."""
    cards = ""

    # Total de registros
    cards += f"""
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                border-radius:12px;padding:14px 18px;min-width:140px;text-align:center;">
        <div style="font-size:22px;font-weight:700;color:#E8253A;">{len(df):,}</div>
        <div style="font-size:11px;color:#9a9a9f;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Registros</div>
    </div>"""

    # Preço médio PIX
    if "preco_pix" in df.columns:
        serie = pd.to_numeric(df["preco_pix"], errors="coerce").dropna()
        if not serie.empty:
            cards += f"""
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                border-radius:12px;padding:14px 18px;min-width:140px;text-align:center;">
        <div style="font-size:22px;font-weight:700;color:#E8253A;">R$ {serie.mean():,.2f}</div>
        <div style="font-size:11px;color:#9a9a9f;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Preço Médio PIX</div>
    </div>"""

    # Menor preço PIX
    if "preco_pix" in df.columns:
        serie = pd.to_numeric(df["preco_pix"], errors="coerce").dropna()
        if not serie.empty:
            cards += f"""
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                border-radius:12px;padding:14px 18px;min-width:140px;text-align:center;">
        <div style="font-size:22px;font-weight:700;color:#4ade80;">R$ {serie.min():,.2f}</div>
        <div style="font-size:11px;color:#9a9a9f;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Menor Preço PIX</div>
    </div>"""

    # Disponíveis
    if "disponibilidade" in df.columns:
        disponiveis = df["disponibilidade"].eq("Disponível").sum()
        cards += f"""
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                border-radius:12px;padding:14px 18px;min-width:140px;text-align:center;">
        <div style="font-size:22px;font-weight:700;color:#4ade80;">{disponiveis:,}</div>
        <div style="font-size:11px;color:#9a9a9f;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Disponíveis</div>
    </div>"""

    if not cards:
        return ""

    return f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px;">
        {cards}
    </div>"""


def _bloco_sql(sql: str) -> str:
    """Renderiza o SQL gerado como bloco colapsável."""
    return f"""
    <details style="margin-top:14px;">
        <summary style="cursor:pointer;color:#9a9a9f;font-size:12px;
                        list-style:none;user-select:none;">
            🗂️ Ver SQL gerado pelo Claude Haiku
        </summary>
        <pre style="background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;padding:14px;font-size:12px;color:#a78bfa;
                    overflow-x:auto;margin-top:8px;white-space:pre-wrap;">{sql}</pre>
    </details>"""


# ── Função principal chamada pelo app.py ──────────────────────────────────────

def processar_mensagem(mensagem: str, db_filter: str = "todas", historico: list = None) -> str:
    """
    Ponto de integração chamado pelo app.py.

    Parâmetros:
        mensagem  : str  — pergunta do usuário
        db_filter : str  — "todas" | "ponte" | "veracruz"
        historico : list — mensagens anteriores (reservado para uso futuro)

    Retorna:
        str — HTML completo para renderizar no chat
    """

    # 1. Executa o pipeline completo (Bedrock → Step Functions → S3)
    resultado = buscar_dados(pergunta=mensagem, base=db_filter)

    # 2. Pipeline falhou
    if not resultado["sucesso"]:
        sql_bloco = _bloco_sql(resultado["sql"]) if resultado.get("sql") else ""
        return f"""
        <span style="color:#f87171;font-weight:600;">❌ Erro na consulta</span><br>
        <span style="color:#9a9a9f;font-size:13px;">{resultado.get('erro', 'Erro desconhecido.')}</span>
        {sql_bloco}
        """

    df  = resultado["df"]
    sql = resultado["sql"]

    # 3. Consulta executou mas não retornou dados
    if df is None or df.empty:
        return f"""
        ✅ Consulta executada com sucesso, mas <strong>nenhum registro</strong>
        correspondeu aos critérios informados.
        {_bloco_sql(sql)}
        """

    # 4. Sucesso — monta resposta com métricas + tabela + SQL
    return f"""
    ✅ Consulta executada com sucesso!
    {_metricas_rapidas(df)}
    {_df_para_html(df)}
    {_bloco_sql(sql)}
    """
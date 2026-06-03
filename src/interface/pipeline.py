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

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import base64
import pandas as pd
from aws_client import buscar_dados


def _csv_data_uri(df: pd.DataFrame) -> str:
    """Converte o DataFrame em um data URI base64 pronto para download via <a href>."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    b64 = base64.b64encode(csv_bytes).decode("utf-8")
    return f"data:text/csv;charset=utf-8;base64,{b64}"


def _chart_payload(df: pd.DataFrame) -> str:
    """
    Constrói o JSON com os dados dos 3 cruzamentos estratégicos.
    Retorna uma string JSON segura para embutir em atributo HTML data-*.
    """
    import json as _json

    FARMACIAS_MAP = {
        "farmaponte": "FarmaPonte",
        "farma ponte": "FarmaPonte",
        "vera cruz": "Vera Cruz",
        "veracruz": "Vera Cruz",
        "drogaria vera cruz": "Vera Cruz",
        "farmazzini": "Farmazzini",
    }

    # Normaliza a coluna farmacia
    df = df.copy()
    if "farmacia" in df.columns:
        df["farmacia"] = df["farmacia"].apply(
            lambda v: FARMACIAS_MAP.get(str(v).strip().lower(), str(v).strip())
            if pd.notna(v) else v
        )
    else:
        # Se o DataFrame não tem coluna farmacia, não há cruzamento competitivo possível
        return ""

    farmacias = sorted(df["farmacia"].dropna().unique().tolist())
    if len(farmacias) < 1:
        return ""

    # ── Cruzamento 1: preço médio por farmácia (original / pix / cartão) ──────
    cruzamento1 = {}
    for mod in ("preco_original", "preco_pix", "preco_cartao"):
        if mod in df.columns:
            serie = pd.to_numeric(df[mod], errors="coerce")
            cruzamento1[mod] = (
                df.assign(_p=serie)
                .groupby("farmacia")["_p"]
                .mean()
                .round(2)
                .reindex(farmacias)
                .fillna(0)
                .to_dict()
            )

    # ── Cruzamento 2: preços por modalidade por farmácia (mesma estrutura,
    #    mas focada na leitura de agressividade vertical) ─────────────────────
    cruzamento2 = cruzamento1  # mesmos dados, gráfico transpõe os eixos no frontend

    # ── Cruzamento 3: share de disponibilidade por farmácia ──────────────────
    cruzamento3 = {}
    if "disponibilidade" in df.columns:
        STATUS_DISPONIVEL = {"disponível", "disponivel", "available", "sim", "yes"}
        df["_disp"] = df["disponibilidade"].apply(
            lambda v: "Disponível"
            if str(v).strip().lower() in STATUS_DISPONIVEL
            else "Indisponível"
            if pd.notna(v)
            else "Indisponível"
        )
        for farm in farmacias:
            sub = df[df["farmacia"] == farm]["_disp"]
            total = len(sub)
            disponivel = int(sub.eq("Disponível").sum())
            cruzamento3[farm] = {
                "disponivel": disponivel,
                "indisponivel": total - disponivel,
                "total": total,
            }

    payload = {
        "farmacias": farmacias,
        "cruzamento1": cruzamento1,
        "cruzamento2": cruzamento2,
        "cruzamento3": cruzamento3,
    }
    # html-safe: escapa aspas simples e caracteres problemáticos
    return _json.dumps(payload, ensure_ascii=False).replace("'", "&#39;")


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

    # 4. Sucesso — monta resposta com métricas + tabela + SQL + botões de ação
    csv_uri = _csv_data_uri(df)
    nome_arquivo = "farmazzini_consulta.csv"
    chart_json = _chart_payload(df)

    # Botão de gráfico só aparece quando há dados competitivos suficientes
    # CORREÇÃO: JSON embutido em onclick quebra por causa das aspas duplas e simples.
    # Solução: gravar o payload num <script> com ID único e referenciar por variável JS.
    import uuid as _uuid
    btn_grafico = ""
    script_payload = ""
    if chart_json:
        payload_var = "chartData_" + _uuid.uuid4().hex[:8]
        # chart_json já tem ensure_ascii=False e &#39; — desfazemos o &#39; aqui pois
        # vamos embutir dentro de um <script>, não de um atributo HTML.
        chart_json_raw = chart_json.replace("&#39;", "'")
        script_payload = f"""<script>
var {payload_var} = {chart_json_raw};
</script>"""
        btn_grafico = f"""
        <button class="action-btn"
                onclick="abrirGrafico({payload_var})"
                style="border-color:rgba(232,37,58,0.35);color:#E8253A;">
            <i class="fa-solid fa-chart-bar"></i> Gerar Gráfico
        </button>"""

    return f"""
    {script_payload}
    ✅ Consulta executada com sucesso!
    {_metricas_rapidas(df)}
    {_df_para_html(df)}
    {_bloco_sql(sql)}
    <div class="action-row" style="margin-top:20px;border-top:1px solid var(--border);padding-top:12px;">
        <a href="{csv_uri}" download="{nome_arquivo}" class="action-btn" style="text-decoration:none;">
            <i class="fa-solid fa-file-csv"></i> Exportar CSV
        </a>
        {btn_grafico}
    </div>
    """
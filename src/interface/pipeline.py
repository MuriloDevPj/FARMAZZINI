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

    CORREÇÃO: Totalmente resiliente — funciona com ou sem coluna 'farmacia',
    e com aliases de colunas calculadas pelo Athena (menor_preco_mercado, etc).
    Só retorna "" se o DataFrame estiver vazio ou sem nenhum dado utilizável.
    """
    import json as _json

    if df is None or df.empty:
        return ""

    FARMACIAS_MAP = {
        "farmaponte": "FarmaPonte",
        "farma ponte": "FarmaPonte",
        "vera cruz": "Vera Cruz",
        "veracruz": "Vera Cruz",
        "drogaria vera cruz": "Vera Cruz",
        "farmazzini": "Farmazzini",
    }

    # Hints para detectar colunas de preço mesmo com aliases do Athena
    PRECO_HINTS = [
        "preco_original", "preco_pix", "preco_cartao",
        "menor_preco", "menor_preco_mercado", "preco_medio",
        "media_preco", "preco_min", "preco_max", "valor",
    ]

    df = df.copy()
    cols_lower = {c.lower(): c for c in df.columns}

    # Normaliza a coluna farmacia se existir (com tolerância a variações de case)
    col_farmacia = cols_lower.get("farmacia")
    if col_farmacia:
        df[col_farmacia] = df[col_farmacia].apply(
            lambda v: FARMACIAS_MAP.get(str(v).strip().lower(), str(v).strip())
            if pd.notna(v) else v
        )
    else:
        # Sem coluna farmacia: tenta detectar coluna de agrupamento pelo nome
        # e cria uma coluna farmacia sintética para manter o pipeline funcionando.
        # Isso cobre queries como SELECT farmacia, MIN(preco) AS menor_preco_mercado ...
        for hint in ("farmacia", "loja", "filial", "unidade"):
            match = next((orig for low, orig in cols_lower.items() if hint in low), None)
            if match:
                df["farmacia"] = df[match]
                col_farmacia = "farmacia"
                break

        # Último recurso: DataFrame sem contexto de farmácia → gráfico genérico
        if not col_farmacia:
            # Descobre coluna de label (não numérica)
            label_col = next(
                (c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])),
                df.columns[0]
            )
            df["farmacia"] = df[label_col].astype(str)
            col_farmacia = "farmacia"

    # Valores que jamais são nomes de farmácia (status de disponibilidade)
    NAO_FARMACIAS = {
        "disponível", "disponivel", "indisponível", "indisponivel",
        "available", "unavailable", "sim", "não", "yes", "no",
    }
    farmacias = sorted([
        v for v in df["farmacia"].dropna().unique().tolist()
        if str(v).strip().lower() not in NAO_FARMACIAS
    ])
    if not farmacias:
        return ""

    # ── Cruzamento 1: preço médio por farmácia ────────────────────────────────
    # Inclui colunas canônicas E aliases gerados pelo Athena (ex: menor_preco_mercado)
    COLUNAS_PRECO_CANONICAS = ("preco_original", "preco_pix", "preco_cartao")
    cruzamento1 = {}

    # 1a. Tenta as colunas canônicas primeiro
    for mod in COLUNAS_PRECO_CANONICAS:
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

    # 1b. Se nenhuma coluna canônica foi encontrada, detecta dinamicamente
    #     qualquer coluna numérica com hint de preco/valor (aliases do Athena)
    if not cruzamento1:
        for col in df.columns:
            if col == "farmacia":
                continue
            if any(h in col.lower() for h in PRECO_HINTS) or pd.api.types.is_numeric_dtype(df[col]):
                serie = pd.to_numeric(df[col], errors="coerce")
                if serie.notna().any():
                    cruzamento1[col] = (
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
    cruzamento2 = cruzamento1  # mesmos dados, gráfico transpoem os eixos no frontend

    # ── Cruzamento 3: share de disponibilidade por farmácia ──────────────────
    # Detecta dois formatos possíveis de retorno do Athena:
    #
    # FORMATO A — pré-agregado (GROUP BY farmacia, disponibilidade + COUNT):
    #   farmacia   | disponibilidade | total
    #   FarmaPonte | Disponível      | 120
    #   FarmaPonte | Indisponível    | 0
    #
    # FORMATO B — linha a linha (SELECT ... disponibilidade FROM tb_processed):
    #   farmacia   | nome      | disponibilidade
    #   FarmaPonte | Dipirona  | Disponível
    #   FarmaPonte | Paracetamol | Indisponível
    #
    cruzamento3 = {}
    if "disponibilidade" in df.columns:
        # BUG FIX: conjunto expandido para cobrir variações com/sem acento e maiúsculas
        # que o Athena pode retornar dependendo de como os dados foram gravados no S3.
        STATUS_DISPONIVEL = {
            "disponível", "disponivel",   # com e sem acento
            "available", "sim", "yes",
            "true", "1", "ativo", "ativa",
        }

        def _is_disponivel(valor) -> bool:
            """Normaliza unicode e case antes de comparar — imune a variações do Athena."""
            import unicodedata
            s = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode().strip().lower()
            return s in {
                "disponivel", "available", "sim", "yes", "true", "1", "ativo", "ativa"
            }

        # Detecta colunas de contagem — hints comuns gerados pelo Athena
        COUNT_HINTS = ("total", "qtd", "count", "quantidade", "contagem", "_c0")
        col_count = next(
            (c for c in df.columns
             if any(h in c.lower() for h in COUNT_HINTS)
             and pd.to_numeric(df[c], errors="coerce").notna().any()),
            None
        )

        # FORMATO A: tem coluna de contagem → dados já agregados por (farmacia, disponibilidade)
        if col_count is not None:
            for farm in farmacias:
                sub = df[df["farmacia"] == farm]
                disp_total = 0
                indisp_total = 0
                for _, row in sub.iterrows():
                    # BUG FIX: pd.to_numeric pode retornar NaN; usar `or 0` falha pois
                    # `NaN or 0` retorna 0 MAS `0 or 0` também retorna 0 — o problema real
                    # é quando NaN vem de uma linha válida que deveria ser contada.
                    # Usamos fillna(0) antes de converter para int.
                    qtd_raw = pd.to_numeric(row[col_count], errors="coerce")
                    qtd = int(qtd_raw) if pd.notna(qtd_raw) else 0
                    if _is_disponivel(row["disponibilidade"]):
                        disp_total += qtd
                    else:
                        indisp_total += qtd
                cruzamento3[farm] = {
                    "disponivel": disp_total,
                    "indisponivel": indisp_total,
                    "total": disp_total + indisp_total,
                }

        # FORMATO B: sem coluna de contagem → cada linha é um produto individual
        else:
            # BUG FIX: usa _is_disponivel (com normalização unicode) em vez do set
            # STATUS_DISPONIVEL, que não cobre variações sem acento retornadas pelo Athena.
            df["_disp"] = df["disponibilidade"].apply(
                lambda v: "Disponível" if pd.notna(v) and _is_disponivel(v) else "Indisponível"
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

    # Botão de gráfico: usa data-attribute em vez de onclick inline
    # CORRECAO BUG 2: onclick inline + JSON gera conflito de aspas.
    # Solucao: embutir o JSON em data-chart='' (aspas simples no HTML)
    # e ler com getAttribute no JS, eliminando qualquer risco de SyntaxError.
    btn_grafico = ""
    if chart_json:
        btn_grafico = f"""
        <button class="action-btn" data-chart='{chart_json}'
                onclick="abrirGrafico(this)"
                style="border-color:rgba(232,37,58,0.35);color:#E8253A;">
            <i class="fa-solid fa-chart-bar"></i> Gerar Gráfico
        </button>"""

    return f"""
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
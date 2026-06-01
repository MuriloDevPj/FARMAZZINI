# ==============================================================================
# alertas.py — Detecção de anomalias comerciais por comparação temporal (48h)
# Projeto Farmazzini | Poli Júnior | Equipe 06
#
# Fluxo:
#   1. Roda uma query no Athena (via Step Functions) que compara o preço_pix
#      de HOJE com o de 48h atrás, para todos os produtos disponíveis.
#   2. Filtra apenas produtos com queda >= LIMIAR_QUEDA_PCT no concorrente.
#   3. Cruza com a lista de alto giro (EANs da Farmazzini) — se não houver
#      lista real, usa fallback por nome de produto estratégico.
#   4. Retorna lista de dicts prontos para renderização visual.
# ==============================================================================

import boto3
import json
import time
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

from utils.config import (
    AWS_REGION,
    STATE_MACHINE_ARN,
    BUCKET_S3_RESULTADOS,
    PREFIXO_S3,
    ATHENA_DATABASE,
    ATHENA_TABLE,
    FARMACIAS_VALIDAS,
    DEFAULT_ANO,
    DEFAULT_MES,
    DEFAULT_DIA,
)

# ── Parâmetros do gatilho de anomalia ─────────────────────────────────────────
LIMIAR_QUEDA_PCT = 15.0   # queda >= 15% dispara alerta
PRECO_FARMAZZINI = None   # se None, usa preco_pix do dia atual como referência

# ── Lista de EANs de alto giro da Farmazzini ──────────────────────────────────
# Substitua por uma consulta real à base de vendas quando disponível.
# Formato: conjunto de strings de EAN.
# Se vazio, o sistema usa fallback por palavras-chave de produtos estratégicos.
EANS_ALTO_GIRO: set[str] = set()

# Fallback: termos que identificam produtos de alto giro por nome
TERMOS_ALTO_GIRO = [
    "dipirona", "paracetamol", "ibuprofeno", "amoxicilina", "losartana",
    "atenolol", "omeprazol", "metformina", "dorflex", "buscopan",
    "rivotril", "fluoxetina", "enalapril", "sinvastatina", "aspirina",
    "nimesulida", "azitromicina", "prednisona", "clonazepam", "sertralina",
]


def _data_48h_atras() -> tuple[str, str, str]:
    """Retorna (ano, mes, dia) de 48 horas atrás com base na data padrão do config."""
    data_hoje = datetime(int(DEFAULT_ANO), int(DEFAULT_MES), int(DEFAULT_DIA))
    data_ref  = data_hoje - timedelta(hours=48)
    return str(data_ref.year), f"{data_ref.month:02d}", f"{data_ref.day:02d}"


def _executar_query_athena(sql: str) -> pd.DataFrame | None:
    """
    Executa SQL via Step Functions e retorna o DataFrame do resultado S3.
    Retorna None em caso de qualquer falha (silencioso — alertas não podem
    quebrar a página principal).
    """
    try:
        sf = boto3.client("stepfunctions", region_name=AWS_REGION)
        exec_resp = sf.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps({"query": sql}),
        )
        exec_arn = exec_resp["executionArn"]

        for _ in range(60):          # timeout de ~60 s
            resp   = sf.describe_execution(executionArn=exec_arn)
            status = resp["status"]
            if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
                break
            time.sleep(1)

        if resp["status"] != "SUCCEEDED":
            return None

        output_json = json.loads(resp.get("output", "{}"))
        query_id    = output_json.get("QueryExecution", {}).get("QueryExecutionId")
        if not query_id:
            return None

        time.sleep(1.5)
        s3  = boto3.client("s3", region_name=AWS_REGION)
        obj = s3.get_object(Bucket=BUCKET_S3_RESULTADOS, Key=f"{PREFIXO_S3}{query_id}.csv")
        return pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))

    except Exception:
        return None


def _sql_comparacao_48h(
    ano_hoje: str, mes_hoje: str, dia_hoje: str,
    ano_ref: str,  mes_ref: str,  dia_ref: str,
) -> str:
    """
    Monta a query que compara preco_pix de hoje vs 48h atrás por (farmacia, ean, nome).
    Retorna apenas produtos com queda >= LIMIAR_QUEDA_PCT e disponíveis hoje.
    """
    farmacias = ", ".join(f"'{f}'" for f in FARMACIAS_VALIDAS)
    return f"""
WITH hoje AS (
    SELECT
        farmacia,
        ean,
        nome,
        TRY_CAST(preco_pix      AS DOUBLE) AS preco_hoje,
        TRY_CAST(preco_original AS DOUBLE) AS preco_original_hoje,
        disponibilidade
    FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
    WHERE farmacia IN ({farmacias})
      AND ano='{ano_hoje}' AND mes='{mes_hoje}' AND dia='{dia_hoje}'
      AND disponibilidade = 'Disponível'
      AND TRY_CAST(preco_pix AS DOUBLE) IS NOT NULL
),
ref AS (
    SELECT
        farmacia,
        ean,
        TRY_CAST(preco_pix AS DOUBLE) AS preco_ref
    FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
    WHERE farmacia IN ({farmacias})
      AND ano='{ano_ref}' AND mes='{mes_ref}' AND dia='{dia_ref}'
      AND TRY_CAST(preco_pix AS DOUBLE) IS NOT NULL
),
comparado AS (
    SELECT
        h.farmacia,
        h.ean,
        h.nome,
        h.preco_hoje,
        h.preco_original_hoje,
        r.preco_ref,
        ROUND((r.preco_ref - h.preco_hoje) / r.preco_ref * 100.0, 1) AS queda_pct
    FROM hoje h
    JOIN ref r
      ON h.farmacia = r.farmacia
     AND h.ean      = r.ean
    WHERE r.preco_ref > 0
      AND h.preco_hoje < r.preco_ref
)
SELECT *
FROM comparado
WHERE queda_pct >= {LIMIAR_QUEDA_PCT}
ORDER BY queda_pct DESC
LIMIT 50
"""


def _e_alto_giro(ean: str, nome: str) -> bool:
    """Verifica se o produto é de alto giro via EAN ou fallback por nome."""
    if EANS_ALTO_GIRO and str(ean) in EANS_ALTO_GIRO:
        return True
    nome_lower = str(nome).lower()
    return any(termo in nome_lower for termo in TERMOS_ALTO_GIRO)


def _formatar_alerta(row: pd.Series, preco_farmazzini: float | None) -> dict:
    """
    Transforma uma linha do DataFrame de anomalias no dict de alerta padronizado.
    Campos do dict:
        farmacia, nome, ean, queda_pct, preco_concorrente, preco_ref,
        diferenca_reais (vs Farmazzini, se disponível), texto
    """
    farmacia        = row["farmacia"]
    nome            = str(row["nome"]).title()
    queda_pct       = float(row["queda_pct"])
    preco_hoje      = float(row["preco_hoje"])
    preco_ref       = float(row.get("preco_ref", 0))

    # Diferença em reais: quanto a Farmazzini está acima do concorrente
    diferenca_reais = None
    trecho_diferenca = ""
    if preco_farmazzini is not None and preco_farmazzini > preco_hoje:
        diferenca_reais  = round(preco_farmazzini - preco_hoje, 2)
        trecho_diferenca = f" Seu preço atual está **R$ {diferenca_reais:.2f}** acima deles."
    elif preco_farmazzini is not None and preco_farmazzini <= preco_hoje:
        trecho_diferenca = " Seu preço está competitivo ou abaixo deles."

    texto = (
        f"⚠️ **Alerta Comercial:** A **{farmacia}** reduziu o preço de "
        f"**{nome}** em **{queda_pct:.1f}%** nas últimas 48 horas "
        f"(de R$ {preco_ref:.2f} → R$ {preco_hoje:.2f}).{trecho_diferenca}"
    )

    return {
        "farmacia":         farmacia,
        "nome":             nome,
        "ean":              str(row.get("ean", "—")),
        "queda_pct":        queda_pct,
        "preco_concorrente": preco_hoje,
        "preco_ref":        preco_ref,
        "diferenca_reais":  diferenca_reais,
        "texto":            texto,
    }


# ── Função principal — chamada pelo componente de alertas ─────────────────────

def buscar_alertas_comerciais() -> list[dict]:
    """
    Ponto de entrada público.

    Executa a comparação 48h no Athena, aplica os filtros de alto giro e
    retorna uma lista (possivelmente vazia) de dicts de alerta prontos para
    renderização. Nunca lança exceção — retorna [] em caso de qualquer falha.

    Returns:
        list[dict]: alertas ordenados por queda_pct decrescente.
                    Cada dict contém: farmacia, nome, ean, queda_pct,
                    preco_concorrente, preco_ref, diferenca_reais, texto.
    """
    try:
        ano_hoje, mes_hoje, dia_hoje = DEFAULT_ANO, DEFAULT_MES, DEFAULT_DIA
        ano_ref,  mes_ref,  dia_ref  = _data_48h_atras()

        sql = _sql_comparacao_48h(
            ano_hoje, mes_hoje, dia_hoje,
            ano_ref,  mes_ref,  dia_ref,
        )

        df = _executar_query_athena(sql)
        if df is None or df.empty:
            return []

        alertas = []
        for _, row in df.iterrows():
            if not _e_alto_giro(row.get("ean", ""), row.get("nome", "")):
                continue
            alertas.append(_formatar_alerta(row, PRECO_FARMAZZINI))

        return alertas

    except Exception:
        return []
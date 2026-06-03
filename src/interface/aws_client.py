# ==============================================================================
# aws_client.py — Integração com Amazon Bedrock, Step Functions e S3
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import boto3
import json
import time
import logging
import pandas as pd
from io import StringIO

# ── Logger de diagnóstico — aparece nos logs do Streamlit Cloud ───────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("farmazzini")

REGION         = "us-east-2"
MODEL_ID       = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
MAX_TOKENS     = 600
API_VERSION    = "bedrock-2023-05-31"
STATE_MACHINE  = "arn:aws:states:us-east-2:906513713169:stateMachine:StateMachine_farmazzini_equipe6"
BUCKET         = "farmazzini-equipe6-ohio"
PREFIXO        = "athena-results/"

# ── Cache em memória — evita repetir o pipeline para a mesma pergunta ─────────
_cache: dict = {}

SQL_PROMPT = """Você é o assistente inteligente de inteligência de mercado da rede Farmazzini.
Sua tarefa é transformar a pergunta em português em uma consulta SQL válida para o Amazon Athena.

Regras Estritas:
1. Retorne APENAS o código SQL puro. Sem explicações, saudações ou markdown (NÃO use ```sql).
2. Banco de dados: "db_farmazzini_gold_equipe6" | Tabela: "tb_processed".
3. Colunas disponíveis: ean (string), nome (string), marca (string), preco_original (float64),
   preco_pix (float64), preco_cartao (float64), desconto_padrao (string), promocoes_especiais (string),
   porcentagem_de_cashback (string), gtin (string), disponibilidade (string).
   - Valores exatos de 'disponibilidade' (case-sensitive): 'Disponível' ou 'Indisponível'
     (sempre com inicial maiúscula — NUNCA use minúsculo).

4. Regras de Ouro para Partições (CRÍTICO):
   - As partições obrigatórias são: farmacia, ano, mes, dia. SEMPRE filtre pelas 4.
   - A coluna 'farmacia' é OBRIGATÓRIA em TODA query — sem exceção. A Lambda de validação
     rejeita qualquer SQL que não contenha o filtro por 'farmacia'.
   - Valores exatos da partição 'farmacia' (case-sensitive): 'FarmaPonte' ou 'Vera Cruz'.
     Normalize variações do usuário automaticamente para o valor exato correto.
   - Se o usuário não especificar a farmácia, use: farmacia IN ('FarmaPonte', 'Vera Cruz')
   - Se o usuário não especificar data, use: ano='2026' AND mes='05' AND dia='26'.

5. Exemplos de filtro correto:
   - "produtos da FarmaPonte"   → WHERE farmacia='FarmaPonte' AND ano='2026' AND mes='05' AND dia='26'
   - "produtos da Vera Cruz"    → WHERE farmacia='Vera Cruz' AND ano='2026' AND mes='05' AND dia='26'
   - "todos os produtos"        → WHERE farmacia IN ('FarmaPonte', 'Vera Cruz') AND ano='2026' AND mes='05' AND dia='26'
   - "produtos indisponíveis"   → WHERE farmacia IN ('FarmaPonte', 'Vera Cruz') AND ano='2026' AND mes='05' AND dia='26' AND disponibilidade='Indisponível'
   - "produtos disponíveis"     → WHERE farmacia IN ('FarmaPonte', 'Vera Cruz') AND ano='2026' AND mes='05' AND dia='26' AND disponibilidade='Disponível'

6. Regras de LIMIT (IMPORTANTE):
   - Use LIMIT apenas quando o usuário pedir explicitamente um número específico
     (ex: "os 5 mais caros", "top 10", "os 3 primeiros").
   - NÃO use LIMIT quando o usuário quiser ver todos os registros de uma categoria
     (ex: "quais produtos estão indisponíveis", "liste todos os produtos com cashback").
   - Para queries com ORDER BY sem número específico, use LIMIT 50.

7. Para ordenação por valores numéricos em colunas string, use TRY_CAST(coluna AS DOUBLE)
   em vez de CAST ou FLOAT.

Pergunta: {user_prompt}"""


def gerar_sql_com_bedrock(user_prompt: str) -> tuple:
    t0 = time.time()
    log.info("🧠 [1/3] Bedrock: gerando SQL para: '%s'", user_prompt[:80])

    client = boto3.client(service_name="bedrock-runtime", region_name=REGION)
    prompt = SQL_PROMPT.replace("{user_prompt}", user_prompt)
    body = json.dumps({
        "anthropic_version": API_VERSION,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    })
    try:
        response = client.invoke_model(modelId=MODEL_ID, body=body)
        response_body = json.loads(response["body"].read())
        sql = response_body["content"][0]["text"].strip()
        log.info("✅ [1/3] Bedrock OK em %.2fs | SQL: %s", time.time() - t0, sql[:120])
        return sql, None
    except Exception as e:
        log.error("❌ [1/3] Bedrock FALHOU em %.2fs | Erro: %s", time.time() - t0, e)
        return "", str(e)


def executar_via_step_functions(sql: str) -> tuple:
    t0 = time.time()
    log.info("⚙️  [2/3] Step Functions: iniciando execução...")

    client = boto3.client(service_name="stepfunctions", region_name=REGION)
    try:
        exec_resp = client.start_execution(
            stateMachineArn=STATE_MACHINE,
            input=json.dumps({"query": sql}),
        )
        exec_arn = exec_resp["executionArn"]
        log.info("   Step Functions: execução iniciada | ARN: ...%s", exec_arn[-20:])

        # Polling com backoff progressivo
        intervalos = [0.5, 0.5, 1, 1, 1, 2, 2, 2, 3, 3, 3, 5]
        for i, intervalo in enumerate(intervalos):
            time.sleep(intervalo)
            status_resp = client.describe_execution(executionArn=exec_arn)
            status = status_resp["status"]
            log.info("   Step Functions: poll #%d (%.1fs acumulado) → %s", i + 1, time.time() - t0, status)
            if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
                break

        log.info("%s [2/3] Step Functions terminou em %.2fs com status: %s",
                 "✅" if status == "SUCCEEDED" else "❌", time.time() - t0, status)
        return status, None, status_resp
    except Exception as e:
        log.error("❌ [2/3] Step Functions FALHOU em %.2fs | Erro: %s", time.time() - t0, e)
        return "FAILED", str(e), {}


def buscar_resultado_s3(status_resp: dict) -> tuple:
    t0 = time.time()
    log.info("📦 [3/3] S3: buscando resultado...")

    client = boto3.client(service_name="s3", region_name=REGION)
    try:
        output_json = json.loads(status_resp.get("output", "{}"))
        query_id = output_json.get("QueryExecution", {}).get("QueryExecutionId")
        if not query_id:
            log.error("❌ [3/3] S3: QueryExecutionId não encontrado no output.")
            return None, "QueryExecutionId não encontrado no output."

        chave_s3 = f"{PREFIXO}{query_id}.csv"
        log.info("   S3: buscando chave: %s", chave_s3)

        # Retry com backoff em vez de sleep fixo
        for tentativa in range(8):
            try:
                obj = client.get_object(Bucket=BUCKET, Key=chave_s3)
                df = pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))
                log.info("✅ [3/3] S3 OK em %.2fs | %d linhas, %d colunas (tentativa %d)",
                         time.time() - t0, len(df), len(df.columns), tentativa + 1)
                return df, None
            except client.exceptions.NoSuchKey:
                espera = 0.5 * (tentativa + 1)
                log.info("   S3: arquivo ainda não disponível, aguardando %.1fs (tentativa %d/8)...", espera, tentativa + 1)
                time.sleep(espera)

        log.error("❌ [3/3] S3: arquivo não encontrado após 8 tentativas (%.2fs)", time.time() - t0)
        return None, "Arquivo CSV não encontrado no S3 após múltiplas tentativas."
    except Exception as e:
        log.error("❌ [3/3] S3 FALHOU em %.2fs | Erro: %s", time.time() - t0, e)
        return None, str(e)


def buscar_dados(pergunta: str, base: str = "todas") -> dict:
    """
    Orquestra o pipeline completo:
    Bedrock → Step Functions → S3

    Retorna:
        dict com chaves: sucesso (bool), df (DataFrame|None), sql (str), erro (str|None)
    """
    t_total = time.time()

    # ── Cache: mesma pergunta + mesma base retorna imediatamente ─────────────
    cache_key = f"{pergunta.strip().lower()}|{base}"
    if cache_key in _cache:
        log.info("⚡ Cache hit para: '%s' | base=%s", pergunta[:60], base)
        return _cache[cache_key]

    log.info("=" * 60)
    log.info("🚀 Pipeline iniciado | pergunta='%s' | base=%s", pergunta[:60], base)

    # 1. Gera o SQL com Bedrock
    sql, erro_sql = gerar_sql_com_bedrock(pergunta)
    if erro_sql or not sql:
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro ao gerar SQL: {erro_sql}"}

    # 2. Injeta filtro de farmácia se o usuário especificou
    if base == "ponte":
        sql = sql.replace(
            "farmacia IN ('FarmaPonte', 'Vera Cruz')",
            "farmacia='FarmaPonte'"
        )
    elif base == "veracruz":
        sql = sql.replace(
            "farmacia IN ('FarmaPonte', 'Vera Cruz')",
            "farmacia='Vera Cruz'"
        )

    # 3. Executa via Step Functions
    status, erro_sf, status_resp = executar_via_step_functions(sql)
    if status != "SUCCEEDED":
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Step Functions falhou: {erro_sf or status}"}

    # 4. Busca resultado no S3
    df, erro_s3 = buscar_resultado_s3(status_resp)
    if erro_s3:
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro ao buscar resultado S3: {erro_s3}"}

    log.info("🏁 Pipeline concluído em %.2fs total", time.time() - t_total)
    log.info("=" * 60)

    resultado = {"sucesso": True, "df": df, "sql": sql, "erro": None}
    _cache[cache_key] = resultado
    return resultado

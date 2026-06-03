# ==============================================================================
# aws_client.py — Integração com Amazon Bedrock, Step Functions e S3
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import boto3
import json
import time
import pandas as pd
from io import StringIO

# Importa constantes diretamente — sem importar deste mesmo arquivo
REGION         = "us-east-2"
MODEL_ID       = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
MAX_TOKENS     = 500
API_VERSION    = "bedrock-2023-05-31"
STATE_MACHINE  = "arn:aws:states:us-east-2:906513713169:stateMachine:StateMachine_farmazzini_equipe6"
BUCKET         = "farmazzini-equipe6-ohio"
PREFIXO        = "athena-results/"

SQL_PROMPT = """Você é o assistente inteligente de inteligência de mercado da rede Farmazzini.
Sua tarefa é transformar a pergunta em português em uma consulta SQL válida para o Amazon Athena.

Regras Estritas:
1. Retorne APENAS o código SQL puro. Sem explicações, saudações ou markdown (NÃO use ```sql).
2. Banco de dados: "db_farmazzini_gold_equipe6" | Tabela: "tb_processed".
3. Colunas disponíveis: ean (string), nome (string), marca (string), preco_original (float64),
   preco_pix (float64), preco_cartao (float64), desconto_padrao (string), promocoes_especiais (string),
   porcentagem_de_cashback (string), gtin (string), disponibilidade (string).

4. Regras de Ouro para Partições (CRÍTICO):
   - As partições são: farmacia, ano, mes, dia. SEMPRE filtre pelas 4 quando aplicável.
   - Valores exatos da partição 'farmacia' (case-sensitive): 'FarmaPonte' ou 'Vera Cruz'.
     Se o usuário escrever variações como 'farmaponte', 'farma ponte', 'vera cruz', normalize
     automaticamente para o valor exato correto.
   - Se o usuário não especificar a farmácia, NÃO filtre por farmacia (busque as duas).
   - Se o usuário não especificar data, use SEMPRE: ano='2026' AND mes='05' AND dia='26'.

5. Exemplos de filtro correto:
   - "produtos da FarmaPonte" -> WHERE farmacia='FarmaPonte' AND ano='2026' AND mes='05' AND dia='26'
   - "produtos da Vera Cruz"  -> WHERE farmacia='Vera Cruz'  AND ano='2026' AND mes='05' AND dia='26'
   - "todos os produtos"      -> WHERE ano='2026' AND mes='05' AND dia='26'

Pergunta: {user_prompt}"""


def gerar_sql_com_bedrock(user_prompt: str) -> tuple:
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
        return sql, None
    except Exception as e:
        return "", str(e)


def executar_via_step_functions(sql: str) -> tuple:
    client = boto3.client(service_name="stepfunctions", region_name=REGION)
    try:
        exec_resp = client.start_execution(
            stateMachineArn=STATE_MACHINE,
            input=json.dumps({"query": sql}),
        )
        exec_arn = exec_resp["executionArn"]
        while True:
            status_resp = client.describe_execution(executionArn=exec_arn)
            status = status_resp["status"]
            if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
                break
            time.sleep(1)
        return status, None, status_resp
    except Exception as e:
        return "FAILED", str(e), {}


def buscar_resultado_s3(status_resp: dict) -> tuple:
    client = boto3.client(service_name="s3", region_name=REGION)
    try:
        output_json = json.loads(status_resp.get("output", "{}"))
        query_id = output_json.get("QueryExecution", {}).get("QueryExecutionId")
        if not query_id:
            return None, "QueryExecutionId não encontrado no output."
        chave_s3 = f"{PREFIXO}{query_id}.csv"
        time.sleep(1.5)
        obj = client.get_object(Bucket=BUCKET, Key=chave_s3)
        df = pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))
        return df, None
    except Exception as e:
        return None, str(e)


# ==============================================================================
# buscar_dados — orquestrador principal chamado pelo endpoint do app.py
# Encadeia: gerar SQL → Step Functions → S3 → retorna dict padronizado
# ==============================================================================

def buscar_dados(pergunta: str, base: str = "todas") -> dict:
    """
    Orquestra o pipeline completo a partir de uma pergunta em linguagem natural.

    Parâmetros:
        pergunta : str  — pergunta do usuário vinda do chatbot
        base     : str  — filtro de farmácia: "todas" | "ponte" | "veracruz"

    Retorna dict com:
        sucesso  : bool
        sql      : str   — SQL gerado pelo Bedrock
        df       : pd.DataFrame | None — resultado do Athena
        erro     : str | None — mensagem de erro se houver
    """

    # 1. Enriquecer a pergunta com o filtro de base selecionado no chatbot
    filtro_map = {
        "ponte":    "Considere apenas produtos da FarmaPonte. ",
        "veracruz": "Considere apenas produtos da Vera Cruz. ",
        "todas":    "",
    }
    prefixo_base = filtro_map.get(base, "")
    pergunta_enriquecida = prefixo_base + pergunta

    # 2. Gerar SQL via Bedrock (Claude Haiku)
    sql, erro_sql = gerar_sql_com_bedrock(pergunta_enriquecida)
    if erro_sql or not sql:
        return {
            "sucesso": False,
            "sql": sql,
            "df": None,
            "erro": f"Erro ao gerar SQL: {erro_sql}",
        }

    # 3. Executar SQL via Step Functions → Athena
    status, erro_sf, status_resp = executar_via_step_functions(sql)
    if status != "SUCCEEDED":
        return {
            "sucesso": False,
            "sql": sql,
            "df": None,
            "erro": f"Step Functions retornou '{status}': {erro_sf}",
        }

    # 4. Buscar resultado CSV no S3
    df, erro_s3 = buscar_resultado_s3(status_resp)
    if erro_s3 or df is None:
        return {
            "sucesso": False,
            "sql": sql,
            "df": None,
            "erro": f"Erro ao ler resultado do S3: {erro_s3}",
        }

    return {
        "sucesso": True,
        "sql": sql,
        "df": df,
        "erro": None,
    }
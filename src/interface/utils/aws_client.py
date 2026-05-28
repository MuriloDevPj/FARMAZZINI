# ==============================================================================
# aws_client.py — Integração com Amazon Bedrock, Step Functions e S3
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import boto3
import json
import time
import pandas as pd
from io import StringIO

REGION         = "us-east-2"
MODEL_ID       = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
MAX_TOKENS     = 600
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

6. Sempre adicione LIMIT 100 ao final de queries que retornam múltiplas linhas, para controle de custo.
7. Para ordenação por valores numéricos em colunas string, use TRY_CAST(coluna AS DOUBLE) em vez de CAST ou FLOAT.

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
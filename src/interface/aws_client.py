# ==============================================================================
# aws_client.py — Integração com Amazon Bedrock, Step Functions e S3
# Projeto Farmazzini | Poli Júnior | Equipe 06
# CORREÇÃO: Resiliência contra loops infinitos e latência de escrita assíncrona
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

4. Regras de Ouro para Partições (CRÍTICO):
   - As partições são: farmacia, ano, mes, dia. SEMPRE filtre pelas 4 quando aplicável.
   - Valores exatos da partição 'farmacia' (case-sensitive): 'FarmaPonte' ou 'Vera Cruz'.
     Se o usuário escrever variações como 'farmaponte', 'farma ponte', 'vera cruz', normalize
     automaticamente para o valor exato correto.
   - Se o usuário não especificar a farmácia, NÃO filtre por farmacia (busque as duas).
   - Se o usuário não especificar data, use SEMPRE: ano='2026' AND mes='05' AND dia='26'.

5. Regras de Performance para Athena (CRÍTICO — evita timeout):
   - NUNCA use ORDER BY em queries sem filtro de nome/produto. ORDER BY força scan total + sort.
   - NUNCA use COALESCE em ORDER BY. Causa full scan obrigatório antes do LIMIT.
   - Para "menor preço" ou "mais barato" SEM especificar produto:
     Use MIN() com GROUP BY farmacia — NÃO use ORDER BY ... LIMIT 1.
     Exemplo: SELECT farmacia, MIN(preco_pix) as menor_pix FROM ... GROUP BY farmacia
   - Para "menor preço" COM produto específico:
     Filtre pelo nome primeiro, ENTÃO use ORDER BY com LIMIT.
     Exemplo: WHERE nome LIKE '%Dipirona%' AND ... ORDER BY preco_pix ASC LIMIT 10
   - Prefira LIMIT 50 no máximo. Nunca omita LIMIT em queries sem filtro de nome.
   - Se a pergunta pedir comparativo entre farmácias, use GROUP BY farmacia com AVG() ou MIN().

6. Exemplos de filtro correto:
   - "produtos da FarmaPonte" → SELECT nome, preco_original FROM tb_processed WHERE farmacia='FarmaPonte' AND ano='2026' AND mes='05' AND dia='26' LIMIT 50
   - "menor preço da dipirona na Vera Cruz" → WHERE nome LIKE '%Dipirona%' AND farmacia='Vera Cruz' AND ano='2026' AND mes='05' AND dia='26' ORDER BY preco_pix ASC LIMIT 10
   - "produto mais barato do mercado" → SELECT farmacia, nome, MIN(preco_pix) as menor_pix FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia, nome ORDER BY menor_pix ASC LIMIT 10
   - "comparar preços entre farmácias" → SELECT farmacia, AVG(preco_original) as preco_medio FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia
"""


def gerar_sql_com_bedrock(pergunta: str) -> tuple:
    """
    Envia a pergunta do utilizador para o Claude via Bedrock.
    Retorna (sql, erro)
    """
    client = boto3.client(service_name="bedrock-runtime", region_name=REGION)
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "messages": [
                {"role": "user", "content": pergunta}
            ],
            "system": SQL_PROMPT
        })

        response = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body
        )

        response_body = json.loads(response.get("body").read())
        sql = response_body["content"][0]["text"].strip()

        # Limpeza preventiva de tags de código markdown
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        return sql, None
    except Exception as e:
        return "", str(e)


def executar_via_step_functions(sql: str) -> tuple:
    """
    Dispara a execução na máquina de estados da AWS.
    Garante o retorno do status e a resposta completa da execução, com timeout seguro de 25 segundos.
    """
    client = boto3.client(service_name="stepfunctions", region_name=REGION)
    try:
        exec_resp = client.start_execution(
            stateMachineArn=STATE_MACHINE,
            input=json.dumps({"query": sql}),
        )
        exec_arn = exec_resp["executionArn"]

        # Evita loop infinito: máximo de 25 tentativas de 1 segundo (Timeout de 25s)
        max_tentativas = 60
        tentativa = 0
        status_resp = {}
        
        while tentativa < max_tentativas:
            status_resp = client.describe_execution(executionArn=exec_arn)
            status = status_resp["status"]
            
            if status == "SUCCEEDED":
                return status, None, status_resp

            if status in ("FAILED", "TIMED_OUT", "ABORTED"):
                # Extrai a causa real do erro registrada pela Step Function
                erro_cause = status_resp.get("cause", "")
                erro_error = status_resp.get("error", "")
                # Tenta extrair motivo do Athena dentro do output
                try:
                    output = json.loads(status_resp.get("output", "{}"))
                    athena_reason = (
                        output.get("QueryExecution", {})
                              .get("Status", {})
                              .get("StateChangeReason", "")
                    )
                except Exception:
                    athena_reason = ""
                detalhes = athena_reason or erro_cause or erro_error or status
                return status, detalhes, status_resp

            time.sleep(1)
            tentativa += 1

        # Caso exceda o tempo de segurança regressa com TIMED_OUT
        return "TIMED_OUT", "A execução na AWS Step Functions excedeu o limite de segurança de 60 segundos.", status_resp
    except Exception as e:
        return "FAILED", str(e), {}


def buscar_resultado_s3(status_resp: dict) -> tuple:
    """
    Recupera de forma resiliente os resultados consolidados no S3,
    tratando a latência assíncrona de escrita do Athena.
    """
    client = boto3.client(service_name="s3", region_name=REGION)
    try:
        output_json = json.loads(status_resp.get("output", "{}"))
        query_id = output_json.get("QueryExecution", {}).get("QueryExecutionId")
        if not query_id:
            return None, "QueryExecutionId não encontrado no output do Step Functions."

        chave_s3 = f"{PREFIXO}{query_id}.csv"
        
        # Exponential Backoff para lidar com eventual consistência e latência de escrita do Athena no S3
        max_retries = 4
        backoff_delay = 0.5 # Começa com meio segundo
        
        for i in range(max_retries):
            try:
                obj = client.get_object(Bucket=BUCKET, Key=chave_s3)
                df = pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))
                return df, None
            except client.exceptions.NoSuchKey:
                if i == max_retries - 1:
                    # Se for a última tentativa, propaga o erro de chave não encontrada
                    return None, f"Arquivo de resultado {chave_s3} ainda não disponível no S3 após {max_retries} tentativas."
                time.sleep(backoff_delay)
                backoff_delay *= 2 # Dobra o tempo de espera para a próxima tentativa (0.5s, 1s, 2s, 4s)
                
    except Exception as e:
        return None, str(e)


def buscar_dados(pergunta: str, base: str = "todas") -> dict:
    """
    Orquestra o pipeline completo:
    Bedrock → Step Functions → S3
    """
    # 1. Gera o SQL com o Bedrock
    sql, erro_sql = gerar_sql_com_bedrock(pergunta)
    if erro_sql or not sql:
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro ao gerar SQL: {erro_sql}"}

    # 2. Injeta o filtro de farmácia se o utilizador especificou
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
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro na execução da Query: {erro_sf or status}"}

    # 4. Busca os dados no S3 com tolerância à latência assíncrona
    df, erro_s3 = buscar_resultado_s3(status_resp)
    if erro_s3:
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro ao coletar dados do S3: {erro_s3}"}

    return {"sucesso": True, "df": df, "sql": sql, "erro": None}
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

4. Regras de Ouro para Partições (CRÍTICO — reduz 99% do custo de scan):
   - As partições são: farmacia, ano, mes, dia. SEMPRE inclua as 4 no WHERE.
   - Valores exatos da partição 'farmacia' (case-sensitive): 'FarmaPonte' ou 'Vera Cruz'.
     Se o usuário escrever variações como 'farmaponte', 'farma ponte', 'vera cruz', normalize
     automaticamente para o valor exato correto.
   - Se o usuário não especificar a farmácia, NÃO filtre por farmacia (busque as duas).
   - Se o usuário não especificar data, use SEMPRE: ano='2026' AND mes='05' AND dia='26'.
   - NUNCA omita as partições de data. Uma query sem ano/mes/dia faz scan completo e causa timeout.

5. Regras de Performance e Compatibilidade para Athena (CRÍTICO — evita timeout e erros):
   - NUNCA use ORDER BY sem filtro de nome/produto específico no WHERE. ORDER BY em tabela inteira
     força full scan + sort e é a principal causa de timeout.
   - NUNCA use COALESCE em ORDER BY. Causa full scan obrigatório antes do LIMIT.
   - NUNCA use QUALIFY — essa cláusula NÃO existe no Athena (é exclusiva do BigQuery/Snowflake).
     Para filtrar por ROW_NUMBER/RANK, envolva em subquery:
     Errado:  SELECT ..., ROW_NUMBER() OVER (...) as rn FROM tb_processed WHERE ... QUALIFY rn = 1
     Correto: SELECT * FROM (SELECT ..., ROW_NUMBER() OVER (...) as rn FROM tb_processed WHERE ...) t WHERE t.rn = 1
   - NUNCA use funções exclusivas de outros bancos: QUALIFY, ILIKE, SAMPLE, PIVOT, UNPIVOT.
   - NUNCA use SELECT * sem LIMIT. Sempre especifique as colunas necessárias.
   - Para "menor preço" ou "mais barato" SEM especificar produto:
     Use MIN() com GROUP BY farmacia — NÃO use ORDER BY ... LIMIT 1.
     Exemplo: SELECT farmacia, MIN(preco_pix) as menor_pix FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia
   - Para "menor preço" COM produto específico:
     Filtre pelo nome primeiro, ENTÃO use ORDER BY com LIMIT.
     Exemplo: SELECT farmacia, nome, preco_pix FROM tb_processed WHERE nome LIKE '%Dipirona%' AND ano='2026' AND mes='05' AND dia='26' ORDER BY preco_pix ASC LIMIT 10
   - Para "estoque crítico" ou "ruptura": use GROUP BY farmacia, disponibilidade com COUNT(*).
     Exemplo: SELECT farmacia, disponibilidade, COUNT(*) as qtd FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia, disponibilidade
   - Use LIMIT 20 para queries com ORDER BY. Use LIMIT 50 para queries sem ORDER BY.
   - Se a pergunta pedir comparativo entre farmácias, use GROUP BY farmacia com AVG() ou MIN().
   - Queries com Window Functions (ROW_NUMBER, RANK) só são aceitáveis quando a subquery
     já filtra por partição (farmacia + ano + mes + dia) E por nome de produto.

6. REGRA OBRIGATÓRIA DE COLUNAS (NUNCA viole esta regra):
   - Toda query que usa SELECT com colunas individuais (não COUNT/MIN/AVG/MAX agregados)
     DEVE incluir OBRIGATORIAMENTE: farmacia, disponibilidade.
   - Toda query que lista produtos individuais DEVE incluir: farmacia, nome, disponibilidade.
   - Exceção permitida: queries de agregação pura (GROUP BY + funções de agregação sem
     colunas individuais de produto) não precisam de disponibilidade na lista do SELECT,
     MAS devem usar GROUP BY farmacia, disponibilidade com COUNT(*).

7. Exemplos de filtro correto:
   - "produtos da FarmaPonte" → SELECT farmacia, nome, preco_original, disponibilidade FROM tb_processed WHERE farmacia='FarmaPonte' AND ano='2026' AND mes='05' AND dia='26' LIMIT 50
   - "menor preço da dipirona na Vera Cruz" → SELECT farmacia, nome, preco_pix, disponibilidade FROM tb_processed WHERE nome LIKE '%Dipirona%' AND farmacia='Vera Cruz' AND ano='2026' AND mes='05' AND dia='26' ORDER BY preco_pix ASC LIMIT 10
   - "produto mais barato do mercado" → SELECT farmacia, MIN(preco_pix) as menor_pix FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia
   - "comparar preços entre farmácias" → SELECT farmacia, AVG(preco_original) as preco_medio, AVG(preco_pix) as medio_pix FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia
   - "estoque crítico" → SELECT farmacia, disponibilidade, COUNT(*) as total FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia, disponibilidade ORDER BY total DESC LIMIT 20
   - "preços de medicamentos" → SELECT farmacia, nome, preco_pix, preco_cartao, disponibilidade FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' LIMIT 50
"""


def _injetar_colunas_essenciais(sql: str) -> str:
    """
    Camada de segurança determinística (pós-LLM).

    Garante que toda query de produto individual contenha farmacia e disponibilidade
    no SELECT, independentemente do que o Bedrock gerou.

    Lógica:
    - Só age em queries SELECT simples (não GROUP BY agregado puro).
    - Nunca toca queries com GROUP BY que já são agregações (COUNT/MIN/AVG).
    - Injeta apenas o que estiver faltando — não duplica colunas.
    """
    import re

    sql_stripped = sql.strip()
    sql_upper    = sql_stripped.upper()

    # Não processa queries que não são SELECT simples
    if not sql_upper.startswith("SELECT"):
        return sql_stripped

    # Queries de agregação pura (GROUP BY com funções de agregação) — não mexer
    # Detecta: tem GROUP BY E tem COUNT/SUM/AVG/MIN/MAX no SELECT
    tem_group_by    = "GROUP BY" in sql_upper
    tem_agregacao   = bool(re.search(r"(COUNT|SUM|AVG|MIN|MAX)\s*\(", sql_upper))
    if tem_group_by and tem_agregacao:
        return sql_stripped

    # Extrai a lista do SELECT (entre SELECT e FROM)
    match = re.match(r"(?i)(SELECT\s+)(.*?)(\s+FROM\s)", sql_stripped, re.DOTALL)
    if not match:
        return sql_stripped

    prefix       = match.group(1)   # "SELECT "
    colunas_str  = match.group(2)   # "nome, preco_pix, ..."
    suffix       = sql_stripped[match.end(2):]  # " FROM tb_processed WHERE ..."

    # Normaliza para comparação
    colunas_lower = colunas_str.lower()

    # Verifica quais colunas essenciais estão faltando
    falta_farmacia       = "farmacia" not in colunas_lower
    falta_disponibilidade = "disponibilidade" not in colunas_lower

    # Não injeta se a query já tem SELECT * (já traz tudo)
    if colunas_str.strip() == "*":
        return sql_stripped

    injecoes = []
    if falta_farmacia:
        injecoes.append("farmacia")
    if falta_disponibilidade:
        injecoes.append("disponibilidade")

    if not injecoes:
        return sql_stripped  # nada a fazer

    novas_colunas = ", ".join(injecoes) + ", " + colunas_str
    sql_corrigido = prefix + novas_colunas + suffix
    return sql_corrigido


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

        # Camada de segurança: garante farmacia + disponibilidade em queries de produto
        sql = _injetar_colunas_essenciais(sql)

        return sql, None
    except Exception as e:
        return "", str(e)


def executar_via_step_functions(sql: str) -> tuple:
    """
    Dispara a execução na máquina de estados da AWS.
    
    Estratégia de polling inteligente:
    - Primeiros 10s: verifica a cada 2s (queries simples já terminam aqui)
    - Entre 10s e 40s: verifica a cada 4s (queries médias com ORDER BY)
    - Acima de 40s: verifica a cada 6s (queries pesadas com Window Functions)
    - Timeout total: 120 segundos
    """
    client = boto3.client(service_name="stepfunctions", region_name=REGION)
    try:
        exec_resp = client.start_execution(
            stateMachineArn=STATE_MACHINE,
            input=json.dumps({"query": sql}),
        )
        exec_arn = exec_resp["executionArn"]

        tempo_total   = 0
        status_resp   = {}
        TIMEOUT_MAX   = 120  # segundos — cobre queries pesadas com Window Functions

        while tempo_total < TIMEOUT_MAX:
            status_resp = client.describe_execution(executionArn=exec_arn)
            status = status_resp["status"]

            if status == "SUCCEEDED":
                return status, None, status_resp

            if status in ("FAILED", "TIMED_OUT", "ABORTED"):
                erro_cause = status_resp.get("cause", "")
                erro_error = status_resp.get("error", "")
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

            # Polling inteligente: intervalo cresce conforme o tempo decorrido
            if tempo_total < 10:
                intervalo = 2
            elif tempo_total < 40:
                intervalo = 4
            else:
                intervalo = 6

            time.sleep(intervalo)
            tempo_total += intervalo

        return "TIMED_OUT", (
            f"A query excedeu {TIMEOUT_MAX}s de execução no Athena. "
            "Dica: tente uma pergunta mais específica (filtre por nome do produto ou farmácia). "
            "Queries com ORDER BY em tabelas grandes são as principais causas de lentidão."
        ), status_resp
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
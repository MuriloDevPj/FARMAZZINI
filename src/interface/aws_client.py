# ==============================================================================
# aws_client.py — Integração com Amazon Bedrock, Step Functions e S3
# Projeto Farmazzini | Poli Júnior | Equipe 06
#
# MELHORIA: Self-Correction Loop para perguntas genéricas/ambíguas
#   - Camada 0: Expansão de intenção (query expansion) antes de gerar SQL
#   - Camada 1: Geração de SQL com prompt rico em contexto
#   - Camada 2: Validação leve + auto-correção em até MAX_SQL_RETRIES tentativas
#   - Camada 3: Injeção determinística de colunas essenciais (pós-LLM)
# ==============================================================================

import boto3
import json
import time
import re
import pandas as pd
from io import StringIO

REGION         = "us-east-2"
MODEL_ID       = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
MAX_TOKENS     = 800
API_VERSION    = "bedrock-2023-05-31"
STATE_MACHINE  = "arn:aws:states:us-east-2:906513713169:stateMachine:StateMachine_farmazzini_equipe6"
BUCKET         = "farmazzini-equipe6-ohio"
PREFIXO        = "athena-results/"

# Número máximo de tentativas no self-correction loop
MAX_SQL_RETRIES = 3

# ==============================================================================
# CAMADA 0 — Prompt de Expansão de Intenção
# Transforma perguntas vagas em intenções estruturadas antes de gerar SQL.
# Isso desacopla a linguagem natural do usuário do prompt técnico de SQL.
# ==============================================================================

INTENT_EXPANSION_PROMPT = """Você é um interpretador de intenções para um sistema de inteligência de mercado farmacêutico.

Sua tarefa é receber uma pergunta em português (que pode ser vaga, genérica ou informal) e reescrevê-la
de forma estruturada e clara para facilitar a geração de SQL preciso.

Regras:
1. Retorne APENAS a intenção reescrita. Sem explicações, sem prefixos como "O usuário quer...".
2. Seja específico sobre: qual métrica interessa (preço, estoque, desconto, cashback), qual escopo
   (todos os produtos, produto específico, comparativo entre farmácias), e qual ordenação ou agregação faz sentido.
3. Se a pergunta mencionar farmácia, normalize: 'farmaponte' → 'FarmaPonte', 'vera cruz' → 'Vera Cruz'.
4. Se a pergunta for muito aberta (ex: "o que tem?", "me mostra algo"), interprete como:
   "Listar os produtos disponíveis com nome, preço PIX e disponibilidade de todas as farmácias."
5. Mantenha em português. Seja conciso (1-2 frases).

Exemplos:
- "quanto tá o remedinho pra dor de cabeça?" → "Listar produtos com nome contendo 'dor de cabeça' ou 'analgésico' ou 'dipirona' ou 'paracetamol', mostrando preço PIX e disponibilidade, ordenado por menor preço."
- "qual mais barato?" → "Encontrar o produto com menor preço PIX entre todas as farmácias, agrupado por farmácia."
- "tem promoção?" → "Listar produtos que possuem promoções especiais ou desconto padrão preenchido, mostrando nome, preço original, preço PIX e promoções especiais."
- "compara as farmácias" → "Comparar preço médio PIX e preço médio original entre FarmaPonte e Vera Cruz, agrupado por farmácia."
- "estoque" → "Mostrar contagem de produtos disponíveis e indisponíveis por farmácia."
"""

# ==============================================================================
# CAMADA 1 — Prompt de Geração de SQL
# ==============================================================================

SQL_PROMPT = """Você é o assistente inteligente de inteligência de mercado da rede Farmazzini.
Sua tarefa é transformar a intenção estruturada abaixo em uma consulta SQL válida para o Amazon Athena.

Regras Estritas:
1. Retorne APENAS o código SQL puro. Sem explicações, saudações ou markdown (NÃO use ```sql).
2. Banco de dados: "db_farmazzini_gold_equipe6" | Tabela: "tb_processed".
3. Colunas disponíveis: ean (string), nome (string), marca (string), preco_original (float64),
   preco_pix (float64), preco_cartao (float64), desconto_padrao (string), promocoes_especiais (string),
   porcentagem_de_cashback (string), gtin (string), disponibilidade (string).

4. Regras de Ouro para Partições (CRÍTICO — reduz 99% do custo de scan):
   - As partições são: farmacia, ano, mes, dia. SEMPRE inclua as 4 no WHERE.
   - Valores exatos da partição 'farmacia' (case-sensitive): 'FarmaPonte' ou 'Vera Cruz'.
     Se a intenção mencionar variações como 'farmaponte', 'farma ponte', 'vera cruz', normalize
     automaticamente para o valor exato correto.
   - Se a intenção não especificar farmácia, NÃO filtre por farmacia (busque as duas).
   - Se a intenção não especificar data, use SEMPRE: ano='2026' AND mes='05' AND dia='26'.
   - NUNCA omita as partições de data. Uma query sem ano/mes/dia faz scan completo e causa timeout.

5. Regras de Performance e Compatibilidade para Athena (CRÍTICO):
   - NUNCA use ORDER BY sem filtro de nome/produto específico no WHERE.
   - NUNCA use COALESCE em ORDER BY.
   - NUNCA use QUALIFY — envolva em subquery com WHERE t.rn = 1.
   - NUNCA use funções exclusivas de outros bancos: QUALIFY, ILIKE, SAMPLE, PIVOT, UNPIVOT.
   - NUNCA use SELECT * sem LIMIT. Sempre especifique as colunas necessárias.
   - Para "menor preço" SEM produto específico: MIN() com GROUP BY farmacia.
   - Para "menor preço" COM produto: filtre pelo nome com LIKE, ENTÃO ORDER BY com LIMIT.
   - Para busca por nome de produto: use LOWER(nome) LIKE LOWER('%termo%') para tolerância a maiúsculas.
   - Para "estoque crítico" ou "ruptura": GROUP BY farmacia, disponibilidade com COUNT(*).
   - Use LIMIT 20 para queries com ORDER BY. Use LIMIT 50 para queries sem ORDER BY.
   - Se comparativo entre farmácias: GROUP BY farmacia com AVG() ou MIN().

6. REGRA OBRIGATÓRIA DE COLUNAS:
   - Toda query que lista produtos individuais DEVE incluir: farmacia, nome, disponibilidade.
   - Queries de agregação pura (GROUP BY + funções de agregação) não precisam de disponibilidade
     na lista do SELECT, MAS devem usar GROUP BY farmacia, disponibilidade com COUNT(*) quando
     o assunto for disponibilidade.

7. Exemplos de mapeamento de intenção → SQL:
   - "Listar produtos disponíveis com nome, preço PIX e disponibilidade de todas as farmácias."
     → SELECT farmacia, nome, preco_pix, disponibilidade FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' LIMIT 50
   - "Menor preço PIX agrupado por farmácia."
     → SELECT farmacia, MIN(preco_pix) as menor_pix FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia
   - "Produtos com nome contendo dipirona ou paracetamol, ordenados por menor preço."
     → SELECT farmacia, nome, preco_pix, disponibilidade FROM tb_processed WHERE (LOWER(nome) LIKE '%dipirona%' OR LOWER(nome) LIKE '%paracetamol%') AND ano='2026' AND mes='05' AND dia='26' ORDER BY preco_pix ASC LIMIT 20
   - "Comparar preço médio PIX entre FarmaPonte e Vera Cruz."
     → SELECT farmacia, AVG(preco_pix) as media_pix, AVG(preco_original) as media_original FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia
   - "Contagem de produtos disponíveis e indisponíveis por farmácia."
     → SELECT farmacia, disponibilidade, COUNT(*) as total FROM tb_processed WHERE ano='2026' AND mes='05' AND dia='26' GROUP BY farmacia, disponibilidade ORDER BY total DESC LIMIT 20
   - "Produtos com promoções especiais preenchidas."
     → SELECT farmacia, nome, preco_original, preco_pix, promocoes_especiais, disponibilidade FROM tb_processed WHERE promocoes_especiais IS NOT NULL AND promocoes_especiais <> '' AND ano='2026' AND mes='05' AND dia='26' LIMIT 50
"""

# ==============================================================================
# CAMADA 2 — Prompt de Auto-Correção (Self-Correction Loop)
# Recebe o SQL inválido + o erro e pede uma versão corrigida.
# ==============================================================================

SQL_CORRECTION_PROMPT = """Você é um especialista em SQL para Amazon Athena.
O SQL abaixo foi gerado para responder a uma intenção de consulta, mas contém um erro.

Sua tarefa é corrigir o SQL e retornar APENAS o SQL corrigido, sem explicações ou markdown.

Regras de correção obrigatórias:
- NUNCA use QUALIFY — substitua por subquery: SELECT * FROM (...) t WHERE t.rn = 1
- NUNCA use ILIKE — substitua por LOWER(coluna) LIKE LOWER('%valor%')
- NUNCA use ORDER BY sem filtro de produto específico no WHERE (causa full scan)
- NUNCA omita as partições: ano='2026' AND mes='05' AND dia='26' no WHERE
- NUNCA omita a partição farmacia quando ela for necessária para filtro
- NUNCA use SELECT * sem LIMIT
- Se o erro mencionar coluna inexistente, remova-a da query
- Se o erro mencionar sintaxe, revise cláusulas incompatíveis com Athena (Presto SQL)
- Mantenha o LIMIT original ou use LIMIT 50 se não houver

Intenção original: {intencao}

SQL com erro:
{sql}

Erro retornado:
{erro}

Retorne apenas o SQL corrigido:"""


# ==============================================================================
# Helpers
# ==============================================================================

def _chamar_bedrock(system_prompt: str, user_content: str) -> tuple[str, str | None]:
    """
    Chama o Claude via Bedrock com system + user message.
    Retorna (texto_resposta, erro_ou_None).
    """
    client = boto3.client(service_name="bedrock-runtime", region_name=REGION)
    try:
        body = json.dumps({
            "anthropic_version": API_VERSION,
            "max_tokens": MAX_TOKENS,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        })
        response = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        response_body = json.loads(response["body"].read())
        texto = response_body["content"][0]["text"].strip()

        # Remove fences de markdown caso apareçam
        if "```sql" in texto:
            texto = texto.split("```sql")[1].split("```")[0].strip()
        elif "```" in texto:
            texto = texto.split("```")[1].split("```")[0].strip()

        return texto, None
    except Exception as e:
        return "", str(e)


def _expandir_intencao(pergunta: str) -> str:
    """
    Camada 0: transforma a pergunta bruta numa intenção estruturada.
    Se a chamada ao Bedrock falhar, retorna a pergunta original (fallback seguro).
    """
    intencao, erro = _chamar_bedrock(INTENT_EXPANSION_PROMPT, pergunta)
    if erro or not intencao:
        return pergunta  # fallback: usa a pergunta original
    return intencao


def _validar_sql_localmente(sql: str) -> tuple[bool, str]:
    """
    Validação leve antes de chamar o Step Functions.
    Detecta os erros mais comuns que o Athena rejeitaria.
    Retorna (is_valido, mensagem_de_erro).

    Regras de detecção:
    - Verifica sintaxe proibida no Athena: QUALIFY, ILIKE
    - Verifica presença das partições de data no WHERE
    - Verifica referência à tabela tb_processed (com ou sem database qualificado e alias)
    - Rejeita ORDER BY apenas quando não há GROUP BY nem HAVING nem filtro de nome
      (queries com GROUP BY/HAVING são agregações legítimas que não causam full scan)
    """
    sql_upper = sql.upper().strip()

    # 1. Deve começar com SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "A query não começa com SELECT."

    # 2. Cláusulas incompatíveis com Athena (Presto SQL)
    if "QUALIFY" in sql_upper:
        return False, "Uso de QUALIFY detectado — não suportado no Athena. Use subquery com WHERE t.rn = 1."

    if "ILIKE" in sql_upper:
        return False, "Uso de ILIKE detectado — não suportado no Athena. Use LOWER(col) LIKE LOWER('%valor%')."

    # 3. Partições de data obrigatórias
    if not re.search(r"ANO\s*=", sql_upper):
        return False, "Partições de data (ano/mes/dia) ausentes no WHERE — causaria full scan."

    # 4. Tabela tb_processed deve estar referenciada
    # Aceita: FROM tb_processed, FROM db_xxx.tb_processed, FROM db_xxx.tb_processed t, etc.
    if not re.search(r"FROM\s+[\w.]*TB_PROCESSED", sql_upper):
        return False, "Tabela tb_processed não referenciada na query."

    # 5. ORDER BY sem agregação nem filtro de produto = risco de full scan
    # Só rejeita quando: tem ORDER BY  E  não tem GROUP BY  E  não tem HAVING  E  não tem filtro de nome
    tem_order_by    = "ORDER BY" in sql_upper
    tem_group_by    = "GROUP BY" in sql_upper
    tem_having      = "HAVING"   in sql_upper
    tem_filtro_nome = bool(re.search(r"LOWER\s*\(\s*[\w.]*NOME\s*\)|[\w.]*NOME\s+LIKE", sql_upper))

    if tem_order_by and not tem_group_by and not tem_having and not tem_filtro_nome:
        return False, "ORDER BY sem GROUP BY nem filtro de produto — risco de full scan e timeout no Athena."

    return True, ""


def _injetar_colunas_essenciais(sql: str) -> str:
    """
    Camada de segurança determinística (pós-LLM).
    Garante que toda query de produto individual contenha farmacia e disponibilidade no SELECT.
    """
    sql_stripped = sql.strip()
    sql_upper    = sql_stripped.upper()

    if not sql_upper.startswith("SELECT"):
        return sql_stripped

    tem_group_by  = "GROUP BY" in sql_upper
    tem_agregacao = bool(re.search(r"(COUNT|SUM|AVG|MIN|MAX)\s*\(", sql_upper))
    if tem_group_by and tem_agregacao:
        return sql_stripped

    match = re.match(r"(?i)(SELECT\s+)(.*?)(\s+FROM\s)", sql_stripped, re.DOTALL)
    if not match:
        return sql_stripped

    prefix      = match.group(1)
    colunas_str = match.group(2)
    suffix      = sql_stripped[match.end(2):]

    if colunas_str.strip() == "*":
        return sql_stripped

    colunas_lower = colunas_str.lower()
    injecoes = []
    if "farmacia" not in colunas_lower:
        injecoes.append("farmacia")
    if "disponibilidade" not in colunas_lower:
        injecoes.append("disponibilidade")

    if not injecoes:
        return sql_stripped

    return prefix + ", ".join(injecoes) + ", " + colunas_str + suffix


# ==============================================================================
# Geração de SQL com Self-Correction Loop
# ==============================================================================

def gerar_sql_com_bedrock(pergunta: str) -> tuple[str, str | None]:
    """
    Pipeline completo de geração de SQL com self-correction loop.

    Fluxo:
      1. Expande a intenção da pergunta (Camada 0)
      2. Gera o SQL a partir da intenção (Camada 1)
      3. Valida localmente o SQL (Camada 2a)
      4. Se inválido, tenta corrigir via Bedrock em até MAX_SQL_RETRIES iterações (Camada 2b)
      5. Injeta colunas essenciais deterministicamente (Camada 3)

    Retorna (sql, erro_ou_None).
    """
    # --- Camada 0: Expansão de intenção ---
    intencao = _expandir_intencao(pergunta)

    # --- Camada 1: Geração inicial de SQL ---
    sql, erro_geracao = _chamar_bedrock(SQL_PROMPT, intencao)
    if erro_geracao or not sql:
        return "", f"Erro ao gerar SQL: {erro_geracao}"

    sql = _injetar_colunas_essenciais(sql)

    # --- Camada 2: Self-correction loop ---
    for tentativa in range(MAX_SQL_RETRIES):
        valido, motivo_erro = _validar_sql_localmente(sql)

        if valido:
            # SQL aprovado — retorna
            return sql, None

        # SQL inválido: tenta corrigir via Bedrock
        if tentativa < MAX_SQL_RETRIES - 1:
            prompt_correcao = SQL_CORRECTION_PROMPT.format(
                intencao=intencao,
                sql=sql,
                erro=motivo_erro,
            )
            sql_corrigido, erro_correcao = _chamar_bedrock(
                "Você é um especialista em SQL para Amazon Athena. Retorne apenas SQL puro, sem markdown.",
                prompt_correcao,
            )

            if erro_correcao or not sql_corrigido:
                # Falha na correção — interrompe o loop
                break

            sql = _injetar_colunas_essenciais(sql_corrigido)
        else:
            # Esgotou as tentativas
            return sql, (
                f"Não foi possível gerar um SQL válido após {MAX_SQL_RETRIES} tentativas. "
                f"Último erro detectado: {motivo_erro}. "
                "Tente reformular a pergunta de forma mais específica."
            )

    # Chegou aqui sem aprovar — retorna com erro
    _, motivo_final = _validar_sql_localmente(sql)
    return sql, (
        f"SQL gerado não passou na validação após {MAX_SQL_RETRIES} tentativas. "
        f"Erro: {motivo_final}"
    )


# ==============================================================================
# Execução e Recuperação de Dados (sem alterações)
# ==============================================================================

def executar_via_step_functions(sql: str) -> tuple:
    """
    Dispara a execução na máquina de estados da AWS.

    Estratégia de polling inteligente:
    - Primeiros 10s: verifica a cada 2s
    - Entre 10s e 40s: verifica a cada 4s
    - Acima de 40s: verifica a cada 6s
    - Timeout total: 120 segundos
    """
    client = boto3.client(service_name="stepfunctions", region_name=REGION)
    try:
        exec_resp = client.start_execution(
            stateMachineArn=STATE_MACHINE,
            input=json.dumps({"query": sql}),
        )
        exec_arn = exec_resp["executionArn"]

        tempo_total = 0
        status_resp = {}
        TIMEOUT_MAX = 120

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
    Recupera os resultados consolidados no S3 com tolerância à latência assíncrona.
    """
    client = boto3.client(service_name="s3", region_name=REGION)
    try:
        output_json = json.loads(status_resp.get("output", "{}"))
        query_id = output_json.get("QueryExecution", {}).get("QueryExecutionId")
        if not query_id:
            return None, "QueryExecutionId não encontrado no output do Step Functions."

        chave_s3 = f"{PREFIXO}{query_id}.csv"

        max_retries   = 4
        backoff_delay = 0.5

        for i in range(max_retries):
            try:
                obj = client.get_object(Bucket=BUCKET, Key=chave_s3)
                df = pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))
                return df, None
            except client.exceptions.NoSuchKey:
                if i == max_retries - 1:
                    return None, (
                        f"Arquivo de resultado {chave_s3} ainda não disponível no S3 "
                        f"após {max_retries} tentativas."
                    )
                time.sleep(backoff_delay)
                backoff_delay *= 2
    except Exception as e:
        return None, str(e)


def buscar_dados(pergunta: str, base: str = "todas") -> dict:
    """
    Orquestra o pipeline completo:
    Expansão de Intenção → Bedrock (SQL) → Self-Correction → Step Functions → S3
    """
    # 1. Gera SQL com self-correction loop
    sql, erro_sql = gerar_sql_com_bedrock(pergunta)
    if erro_sql or not sql:
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro ao gerar SQL: {erro_sql}"}

    # 2. Injeta filtro de farmácia se especificado pelo usuário na UI
    if base == "ponte":
        sql = re.sub(
            r"farmacia\s*IN\s*\('FarmaPonte',\s*'Vera Cruz'\)",
            "farmacia='FarmaPonte'",
            sql,
        )
    elif base == "veracruz":
        sql = re.sub(
            r"farmacia\s*IN\s*\('FarmaPonte',\s*'Vera Cruz'\)",
            "farmacia='Vera Cruz'",
            sql,
        )

    # 3. Executa via Step Functions
    status, erro_sf, status_resp = executar_via_step_functions(sql)
    if status != "SUCCEEDED":
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro na execução da Query: {erro_sf or status}"}

    # 4. Busca os dados no S3
    df, erro_s3 = buscar_resultado_s3(status_resp)
    if erro_s3:
        return {"sucesso": False, "df": None, "sql": sql, "erro": f"Erro ao coletar dados do S3: {erro_s3}"}

    return {"sucesso": True, "df": df, "sql": sql, "erro": None}
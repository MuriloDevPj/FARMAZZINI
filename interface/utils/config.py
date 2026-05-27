# ==============================================================================
# config.py — Configurações globais, variáveis de ambiente e constantes AWS
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

# ── Região e serviços AWS ──────────────────────────────────────────────────────
AWS_REGION = "us-east-2"

# ── Amazon Bedrock ─────────────────────────────────────────────────────────────
BEDROCK_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
BEDROCK_MAX_TOKENS = 500
BEDROCK_ANTHROPIC_VERSION = "bedrock-2023-05-31"

# ── Step Functions ─────────────────────────────────────────────────────────────
STATE_MACHINE_ARN = (
    "arn:aws:states:us-east-2:906513713169:stateMachine:StateMachine_farmazzini_equipe6"
)

# ── Amazon S3 ──────────────────────────────────────────────────────────────────
BUCKET_S3_RESULTADOS = "farmazzini-equipe6-ohio"
PREFIXO_S3 = "athena-results/"

# ── Athena / Schema ────────────────────────────────────────────────────────────
ATHENA_DATABASE = "db_farmazzini_gold_equipe6"
ATHENA_TABLE = "tb_processed"

# Valores exatos das partições de farmácia (case-sensitive no S3/Athena)
FARMACIAS_VALIDAS = ["FarmaPonte", "Vera Cruz"]

# Data padrão de consulta (último dia com dados carregados)
DEFAULT_ANO = "2026"
DEFAULT_MES = "05"
DEFAULT_DIA = "26"

# ── Prompt template para geração de SQL ───────────────────────────────────────
SQL_SYSTEM_PROMPT = f"""Você é o assistente inteligente de inteligência de mercado da rede Farmazzini.
Sua tarefa é transformar a pergunta em português em uma consulta SQL válida para o Amazon Athena.

Regras Estritas:
1. Retorne APENAS o código SQL puro. Sem explicações, saudações ou markdown (NÃO use ```sql).
2. Banco de dados: "{ATHENA_DATABASE}" | Tabela: "{ATHENA_TABLE}".
3. Colunas disponíveis: ean (string), nome (string), marca (string), preco_original (float64),
   preco_pix (float64), preco_cartao (float64), desconto_padrao (string), promocoes_especiais (string),
   porcentagem_de_cashback (string), gtin (string), disponibilidade (string).

4. Regras de Ouro para Partições (CRÍTICO):
   - As partições são: farmacia, ano, mes, dia. SEMPRE filtre pelas 4 quando aplicável.
   - Valores exatos da partição 'farmacia' (case-sensitive): 'FarmaPonte' ou 'Vera Cruz'.
     Se o usuário escrever variações como 'farmaponte', 'farma ponte', 'vera cruz', normalize
     automaticamente para o valor exato correto.
   - Se o usuário não especificar a farmácia, NÃO filtre por farmacia (busque as duas).
   - Se o usuário não especificar data, use SEMPRE: ano='{DEFAULT_ANO}' AND mes='{DEFAULT_MES}' AND dia='{DEFAULT_DIA}'.

5. Exemplos de filtro correto:
   - "produtos da FarmaPonte" → WHERE farmacia='FarmaPonte' AND ano='{DEFAULT_ANO}' AND mes='{DEFAULT_MES}' AND dia='{DEFAULT_DIA}'
   - "produtos da Vera Cruz"  → WHERE farmacia='Vera Cruz'  AND ano='{DEFAULT_ANO}' AND mes='{DEFAULT_MES}' AND dia='{DEFAULT_DIA}'
   - "todos os produtos"      → WHERE ano='{DEFAULT_ANO}' AND mes='{DEFAULT_MES}' AND dia='{DEFAULT_DIA}'

Pergunta: {{user_prompt}}"""
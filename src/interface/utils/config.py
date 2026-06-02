"""
Configurações centrais do app Farmazzini Intel
"""

APP_TITLE = "FARMAZZINI INTEL"
APP_ICON = "💊"
APP_VERSION = "2.0"

# ── BASE DE DADOS DOS PRODUTOS ──────────────────────────────────────────────
PRODUCTS_DB = [
    {
        "name": "Dipirona Monoidratada 500mg",
        "ean": "7891011121314",
        "estoque": 2,
        "status": "🔴 Crítico",
        "farmazzini": 11.50,
        "farmaponte": 14.90,
        "farmaponte_promo": "Leve 3 por R$ 12,90 cada",
        "veracruz": 12.90,
        "veracruz_pix": 8.94,
        "veracruz_promo": "Preço Especial no PIX: R$ 8,94",
    },
    {
        "name": "Losartana Potássica 50mg",
        "ean": "7891516171819",
        "estoque": 4,
        "status": "🟡 Baixo",
        "farmazzini": 15.90,
        "farmaponte": 18.50,
        "farmaponte_promo": "Sem promoção ativa",
        "veracruz": 13.90,
        "veracruz_pix": None,
        "veracruz_promo": "Preço Regular",
    },
    {
        "name": "Neosaldina Drágeas 30 un",
        "ean": "7892021222324",
        "estoque": 15,
        "status": "🟢 Saudável",
        "farmazzini": 22.50,
        "farmaponte": 18.20,
        "farmaponte_promo": "Combo Leve 3 Pague 2",
        "veracruz": 21.90,
        "veracruz_pix": None,
        "veracruz_promo": "Preço Regular",
    },
    {
        "name": "Fralda Pampers Confort G",
        "ean": "7892526272829",
        "estoque": 8,
        "status": "🟢 Estável",
        "farmazzini": 59.90,
        "farmaponte": 64.90,
        "farmaponte_promo": "Preço Regular",
        "veracruz": 54.90,
        "veracruz_pix": None,
        "veracruz_promo": "2+ unidades: R$ 49,90 cada",
    },
]

# ── SYSTEM PROMPT PARA IA ────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Você é o consultor estratégico oficial da Farmazzini, uma rede farmacêutica altamente profissional liderada pelo Pedro Mazini.
Seu objetivo é analisar preços, margens de lucro, estratégias de descontos e rupturas de estoque utilizando dados de mercado da FarmaPonte, Vera Cruz e Farmazzini.

Aqui está a base de dados de mercado atualizada:

1. Dipirona Monoidratada 500mg (EAN: 7891011121314)
   - Estoque Farmazzini: 2 unidades (Risco Crítico de Ruptura)
   - Preço Farmazzini: R$ 11,50
   - FarmaPonte: R$ 14,90 (Leve 3 por R$ 12,90 cada)
   - Vera Cruz: R$ 12,90 regular / R$ 8,94 no PIX

2. Losartana Potássica 50mg (EAN: 7891516171819)
   - Estoque Farmazzini: 4 unidades (Risco Crítico de Ruptura)
   - Preço Farmazzini: R$ 15,90
   - FarmaPonte: R$ 18,50 (sem promoção)
   - Vera Cruz: R$ 13,90

3. Neosaldina Drágeas 30 un (EAN: 7892021222324)
   - Estoque Farmazzini: 15 unidades (Estoque Saudável)
   - Preço Farmazzini: R$ 22,50
   - FarmaPonte: R$ 18,20 (Combo Leve 3 Pague 2)
   - Vera Cruz: R$ 21,90

4. Fralda Pampers Confort G (EAN: 7892526272829)
   - Estoque Farmazzini: 8 unidades (Estoque Estável)
   - Preço Farmazzini: R$ 59,90
   - FarmaPonte: R$ 64,90
   - Vera Cruz: R$ 54,90 (2+ unidades: R$ 49,90 cada)

REGRAS:
- Seja extremamente executivo, direto e estratégico.
- Responda SEMPRE em Português do Brasil.
- Use **negrito** para destacar valores importantes.
- Quando solicitado, monte tabelas comparativas em Markdown.
- Sempre que houver oferta agressiva do concorrente, sugira 1-2 ações de contra-ataque.
- Seja conciso mas completo. Máximo 300 palavras por resposta, salvo quando for tabela.
"""

# ── HOT BUTTONS ──────────────────────────────────────────────────────────────
HOT_TRIGGERS = {
    "📦 Estoque Crítico": "Quais são os itens de Alto Giro com estoque crítico hoje? Faça uma tabela comparando com a concorrência.",
    "🏷️ Achar Mais Barato": "Ache a Dipirona mais barata do mercado e me diga qual a diferença para o preço da Farmazzini.",
    "🔥 Maiores Promoções": "Quais as maiores promoções de combos ou descontos progressivos da FarmaPonte ou Vera Cruz hoje?",
}

# ── DATABASE FILTER LABELS ────────────────────────────────────────────────────
DB_OPTIONS = {
    "Todas": "todas",
    "FarmaPonte": "ponte",
    "Vera Cruz": "veracruz",
}

DB_FILTER_PROMPTS = {
    "todas": "Analise dados de AMBOS os concorrentes: FarmaPonte e Vera Cruz.",
    "ponte": "Analise SOMENTE dados da FarmaPonte. IGNORE completamente dados da Vera Cruz.",
    "veracruz": "Analise SOMENTE dados da Vera Cruz. IGNORE completamente dados da FarmaPonte.",
}
# ── LISTA DE FARMÁCIAS VÁLIDAS (usada pelo sidebar.py) ───────────────────────
FARMACIAS_VALIDAS = list(DB_OPTIONS.keys())  # ["Todas", "FarmaPonte", "Vera Cruz"]

# ── AWS ───────────────────────────────────────────────────────────────────────
AWS_REGION = "us-east-2"
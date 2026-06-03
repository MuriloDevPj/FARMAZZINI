"""
╔══════════════════════════════════════════════════════════════════╗
║                FARMAZZINI INTEL — PIPELINE DE DADOS             ║
║                                                                  ║
║  Este arquivo é onde TODA a lógica de negócio vive.             ║
║  Substitua as funções marcadas com ▼ pela sua implementação.    ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────
# IMPORTS — adicione suas bibliotecas aqui
# ─────────────────────────────────────────────
# import psycopg2          # PostgreSQL
# import sqlalchemy        # ORM genérico
# import pandas as pd      # Manipulação de dados
# import google.generativeai as genai  # Gemini SDK
# from langchain...        # LangChain pipeline
# from sentence_transformers import ...  # Busca semântica


def processar_mensagem(mensagem: str, db_filter: str, historico: list) -> str:
    """
    Função principal chamada pelo app.py a cada mensagem do usuário.

    Parâmetros:
    -----------
    mensagem : str
        Texto digitado pelo usuário no input do chat.

    db_filter : str
        Base de dados selecionada na sidebar.
        Valores possíveis: "todas" | "ponte" | "veracruz"

    historico : list
        Lista de mensagens anteriores do chat ativo.
        Formato: [{"sender": "user"|"bot", "text": "..."}]

    Retorna:
    --------
    str
        HTML ou texto plano com a resposta do bot.
        Pode conter tags HTML como <strong>, <table>, etc.

    Fluxo esperado:
    ---------------
    mensagem → pré_processar() → montar_query() → executar_query() → formatar_resposta()
    """

    # ════════════════════════════════════════════════════════
    # ETAPA 1 — PRÉ-PROCESSAMENTO
    # Normalize, limpe ou classifique a mensagem do usuário.
    # ════════════════════════════════════════════════════════
    mensagem_limpa = pre_processar(mensagem)

    # ════════════════════════════════════════════════════════
    # ETAPA 2 — CONSTRUÇÃO DA QUERY
    # Monte a query SQL, semântica ou de API com base
    # na mensagem e no filtro de base selecionado.
    # ════════════════════════════════════════════════════════
    query = montar_query(mensagem_limpa, db_filter)

    # ════════════════════════════════════════════════════════
    # ETAPA 3 — EXECUÇÃO NA BASE DE DADOS
    # Execute a query e obtenha os resultados brutos.
    # ════════════════════════════════════════════════════════
    resultado_bruto = executar_query(query)

    # ════════════════════════════════════════════════════════
    # ETAPA 4 — FORMATAÇÃO DA RESPOSTA
    # Converta os dados brutos em HTML legível para o chat.
    # ════════════════════════════════════════════════════════
    resposta_html = formatar_resposta(resultado_bruto, mensagem_limpa)

    return resposta_html


# ─────────────────────────────────────────────────────────────────
# ▼ ETAPA 1 — PRÉ-PROCESSAMENTO
# ─────────────────────────────────────────────────────────────────
def pre_processar(mensagem: str) -> str:
    """
    ▼ SUBSTITUA esta função pela sua lógica de pré-processamento.

    Sugestões:
    - Remover stopwords
    - Normalizar (lowercase, acentos)
    - Classificar intenção (intent detection)
    - Extrair entidades (NER): nome de produto, EAN, etc.
    - Chamar um modelo para classificação (ex: Gemini, GPT)

    Exemplo de uso futuro:
        intenção = classificar_intencao(mensagem)  # "preço" | "estoque" | "promoção"
        entidades = extrair_entidades(mensagem)     # {"produto": "Dipirona", "ean": "..."}
    """
    return mensagem.lower().strip()


# ─────────────────────────────────────────────────────────────────
# ▼ ETAPA 2 — CONSTRUÇÃO DA QUERY
# ─────────────────────────────────────────────────────────────────
def montar_query(mensagem: str, db_filter: str) -> dict:
    """
    ▼ SUBSTITUA esta função pelo seu Query Builder.

    Deve retornar um dict com tudo que executar_query() precisa.
    O formato é livre — defina conforme sua arquitetura.

    Exemplos de retorno:

    Para SQL:
        return {
            "tipo": "sql",
            "sql": "SELECT * FROM produtos WHERE nome LIKE %s",
            "params": ("%dipirona%",),
            "db": db_filter
        }

    Para API (Gemini/OpenAI):
        return {
            "tipo": "api",
            "prompt": mensagem,
            "db_filter": db_filter,
            "system_instruction": "Você é um consultor..."
        }

    Para busca vetorial:
        return {
            "tipo": "vetor",
            "embedding": gerar_embedding(mensagem),
            "top_k": 5,
            "filtro_db": db_filter
        }
    """
    # ── STUB: retorna a mensagem para a resposta de fallback ──
    return {
        "tipo": "stub",
        "mensagem_original": mensagem,
        "db_filter": db_filter
    }


# ─────────────────────────────────────────────────────────────────
# ▼ ETAPA 3 — EXECUÇÃO NA BASE DE DADOS
# ─────────────────────────────────────────────────────────────────
def executar_query(query: dict) -> dict:
    """
    ▼ SUBSTITUA esta função pela sua execução real.

    Recebe o dict de montar_query() e retorna os dados brutos.

    Exemplos por tipo:

    SQL (psycopg2):
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(query["sql"], query["params"])
        rows = cur.fetchall()
        return {"tipo": "tabela", "colunas": [...], "linhas": rows}

    Gemini SDK:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(query["prompt"])
        return {"tipo": "texto", "conteudo": response.text}

    Busca vetorial (FAISS/Pinecone):
        resultados = index.search(query["embedding"], k=query["top_k"])
        return {"tipo": "documentos", "hits": resultados}
    """
    # ── STUB: resposta de demonstração ──
    return {
        "tipo": "stub",
        "mensagem": query.get("mensagem_original", ""),
        "db_filter": query.get("db_filter", "todas")
    }


# ─────────────────────────────────────────────────────────────────
# ▼ ETAPA 4 — FORMATAÇÃO DA RESPOSTA
# ─────────────────────────────────────────────────────────────────
def formatar_resposta(resultado: dict, mensagem_original: str) -> str:
    """
    ▼ SUBSTITUA esta função pelo seu formatador.

    Converte os dados brutos em HTML para o chat.

    Exemplos de retorno:

    Tabela HTML:
        return '''
            <div class="table-container">
                <table>
                    <thead><tr><th>Produto</th><th>Preço</th></tr></thead>
                    <tbody>
                        <tr><td>Dipirona 500mg</td><td>R$ 11,50</td></tr>
                    </tbody>
                </table>
            </div>
        '''

    Texto com formatação:
        return f"<strong>Resultado:</strong> {resultado['conteudo']}"

    Erro amigável:
        return "❌ Nenhum resultado encontrado para sua consulta."
    """
    # ── STUB: resposta de demonstração até o pipeline estar pronto ──
    db_names = {"todas": "Todas as bases", "ponte": "FarmaPonte", "veracruz": "Vera Cruz"}
    db_label = db_names.get(resultado.get("db_filter", "todas"), "Todas")

    return f"""
        <div style="border-left: 3px solid var(--primary); padding-left: 12px;">
            <strong style="color: var(--primary);">⚙️ Pipeline em desenvolvimento</strong>
        </div>
        <br>
        Recebi sua consulta: <strong>"{resultado.get('mensagem', '')}"</strong><br>
        Base ativa: <strong>{db_label}</strong><br><br>
        <span style="color: var(--text-muted); font-size: 13px;">
            ℹ️ Substitua as funções em <code>pipeline.py</code> para retornar dados reais.
        </span>
    """

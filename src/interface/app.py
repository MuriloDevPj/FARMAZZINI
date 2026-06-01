
# ==============================================================================
# app.py — Farmazzini Intel 2.0
# Arquitetura: HTML component injetado via st.components + backend AWS
# ==============================================================================
 
import sys
import os
 
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
 
import streamlit as st
import streamlit.components.v1 as components
import boto3
import json
import time
import pandas as pd
from io import StringIO
 
st.set_page_config(
    page_title="Farmazzini Intel",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
 
# Oculta chrome do Streamlit
st.markdown("""
<style>
#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"] { background: #060608; }
</style>
""", unsafe_allow_html=True)
 
# ── Credenciais AWS ───────────────────────────────────────────────────────────
os.environ["AWS_ACCESS_KEY_ID"]     = st.secrets.get("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_DEFAULT_REGION"]    = st.secrets.get("AWS_DEFAULT_REGION", "us-east-2")
 
# ── Config AWS ────────────────────────────────────────────────────────────────
REGION        = "us-east-2"
MODEL_ID      = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
STATE_MACHINE = "arn:aws:states:us-east-2:906513713169:stateMachine:StateMachine_farmazzini_equipe6"
BUCKET        = "farmazzini-equipe6-ohio"
PREFIXO       = "athena-results/"
 
SQL_PROMPT = """Você é o assistente inteligente de inteligência de mercado da rede Farmazzini.
Transforme a pergunta em SQL válido para o Amazon Athena.
 
Regras:
1. Retorne APENAS código SQL puro, sem markdown ou explicações.
2. Banco: "db_farmazzini_gold_equipe6" | Tabela: "tb_processed"
3. Colunas: ean, nome, marca, preco_original, preco_pix, preco_cartao, desconto_padrao, promocoes_especiais, porcentagem_de_cashback, gtin, disponibilidade
4. Valores exatos de disponibilidade: 'Disponível' ou 'Indisponível' (inicial maiúscula)
5. Partições OBRIGATÓRIAS: farmacia, ano, mes, dia
6. farmacia É OBRIGATÓRIO em TODA query. Se não especificado: farmacia IN ('FarmaPonte', 'Vera Cruz')
7. Se não especificar data: ano='2026' AND mes='05' AND dia='26'
8. Valores exatos de farmacia: 'FarmaPonte' ou 'Vera Cruz'
9. Para busca por nome: LOWER(nome) LIKE '%termo%'
10. LIMIT apenas quando pedir número específico. Para listagens completas, sem LIMIT.
11. Para ordenar desconto: TRY_CAST(REPLACE(desconto_padrao,'%','') AS DOUBLE)
12. SEMPRE inclua farmacia e nome no SELECT
 
Pergunta: {user_prompt}"""
 
# ── Funções AWS ───────────────────────────────────────────────────────────────
 
def gerar_sql(prompt: str, farmacia_filtro: str = None) -> tuple:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    p = prompt
    if farmacia_filtro:
        p = f"{prompt} (considere apenas farmacia='{farmacia_filtro}')"
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 800,
        "messages": [{"role": "user", "content": SQL_PROMPT.replace("{user_prompt}", p)}],
    })
    try:
        r = client.invoke_model(modelId=MODEL_ID, body=body)
        sql = json.loads(r["body"].read())["content"][0]["text"].strip()
        return sql, None
    except Exception as e:
        return "", str(e)
 
 
def executar_sql(sql: str) -> tuple:
    client = boto3.client("stepfunctions", region_name=REGION)
    try:
        exec_resp = client.start_execution(
            stateMachineArn=STATE_MACHINE,
            input=json.dumps({"query": sql}),
        )
        exec_arn = exec_resp["executionArn"]
        while True:
            resp = client.describe_execution(executionArn=exec_arn)
            status = resp["status"]
            if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
                break
            time.sleep(1)
        return status, None, resp
    except Exception as e:
        return "FAILED", str(e), {}
 
 
def buscar_s3(status_resp: dict) -> tuple:
    client = boto3.client("s3", region_name=REGION)
    try:
        output = json.loads(status_resp.get("output", "{}"))
        qid = output.get("QueryExecution", {}).get("QueryExecutionId")
        if not qid:
            return None, "QueryExecutionId não encontrado."
        time.sleep(1.5)
        obj = client.get_object(Bucket=BUCKET, Key=f"{PREFIXO}{qid}.csv")
        df = pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))
        return df, None
    except Exception as e:
        return None, str(e)
 
 
def gerar_contra_ataque(contexto: str) -> str:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": (
            f"Com base nestes dados de mercado farmacêutico:\n{contexto}\n\n"
            "Gere 2 planos de ação rápidos e práticos de marketing ou precificação "
            "para a Farmazzini contra-atacar e preservar sua margem de lucro. "
            "Seja direto, executivo e focado em táticas reais de farmácia. "
            "Use negrito com ** para destacar pontos importantes."
        )}],
    })
    try:
        r = client.invoke_model(modelId=MODEL_ID, body=body)
        return json.loads(r["body"].read())["content"][0]["text"].strip()
    except Exception as e:
        return f"Erro ao gerar contra-ataque: {e}"
 
 
# ── Processamento via query params (comunicação JS → Python) ──────────────────
query_params = st.query_params
 
if "action" in query_params:
    action = query_params.get("action", "")
    pergunta = query_params.get("pergunta", "")
    farmacia = query_params.get("farmacia", "") or None
 
    if action == "query" and pergunta:
        sql, erro = gerar_sql(pergunta, farmacia)
        if erro:
            result = {"ok": False, "error": erro, "sql": ""}
        else:
            status, erro2, status_resp = executar_sql(sql)
            if erro2 or status != "SUCCEEDED":
                result = {"ok": False, "error": erro2 or f"Status: {status}", "sql": sql}
            else:
                df, erro3 = buscar_s3(status_resp)
                if erro3:
                    result = {"ok": False, "error": erro3, "sql": sql}
                elif df is None or df.empty:
                    result = {"ok": True, "sql": sql, "rows": [], "columns": [], "empty": True}
                else:
                    result = {
                        "ok": True,
                        "sql": sql,
                        "columns": df.columns.tolist(),
                        "rows": df.fillna("—").values.tolist(),
                        "csv": df.to_csv(index=False),
                        "empty": False,
                    }
        st.json(result)
        st.stop()
 
    elif action == "attack" and pergunta:
        texto = gerar_contra_ataque(pergunta)
        st.json({"ok": True, "texto": texto})
        st.stop()
 
 
# ── Interface HTML principal ──────────────────────────────────────────────────
html_interface = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
:root {
    --bg-main: #060608;
    --bg-sidebar: rgba(12, 12, 16, 0.95);
    --bg-card: #0b0b0d;
    --primary: #E63946;
    --primary-dark: #8B0000;
    --text-main: #ffffff;
    --text-muted: #9a9a9f;
    --border: rgba(255, 255, 255, 0.06);
    --glow-red: rgba(230, 57, 70, 0.22);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Urbanist', sans-serif;
    background-color: var(--bg-main);
    color: var(--text-main);
    display: flex;
    height: 100vh;
    overflow: hidden;
    position: relative;
}
.fluid-glow-1 {
    position: fixed; top: -15%; left: 20%; width: 60vw; height: 60vw;
    background: radial-gradient(circle, var(--glow-red) 0%, rgba(139,0,0,0.05) 50%, transparent 75%);
    filter: blur(100px); z-index: 0; pointer-events: none; border-radius: 50%;
}
.fluid-glow-2 {
    position: fixed; bottom: -10%; right: 10%; width: 50vw; height: 50vw;
    background: radial-gradient(circle, rgba(230,57,70,0.15) 0%, rgba(139,0,0,0.03) 60%, transparent 80%);
    filter: blur(100px); z-index: 0; pointer-events: none; border-radius: 50%;
}
/* SIDEBAR */
.sidebar {
    position: fixed; top: 16px; left: 16px; bottom: 16px; width: 300px;
    background: var(--bg-sidebar); border: 1px solid var(--border);
    border-radius: 24px; display: flex; flex-direction: column;
    padding: 24px 18px; gap: 16px; z-index: 10;
    backdrop-filter: blur(25px); box-shadow: 0 16px 40px rgba(0,0,0,0.7);
    transition: transform 0.35s cubic-bezier(0.25,0.8,0.25,1), opacity 0.35s ease;
}
.sidebar.collapsed { transform: translateX(-332px); opacity: 0; pointer-events: none; }
.sidebar-title { font-size: 12px; text-transform: uppercase; letter-spacing: 2.5px; color: var(--primary); font-weight: 700; }
.sidebar-header { display: flex; align-items: center; justify-content: space-between; }
 
/* DB PILLS */
.db-selector { background: rgba(255,255,255,0.03); padding: 12px; border-radius: 16px; border: 1px solid var(--border); }
.db-label { font-size: 10px; text-transform: uppercase; color: var(--text-muted); font-weight: 700; letter-spacing: 1px; margin-bottom: 8px; }
.db-pills { display: flex; background: rgba(0,0,0,0.4); border-radius: 10px; padding: 3px; border: 1px solid rgba(255,255,255,0.05); }
.db-pill { flex: 1; padding: 8px; text-align: center; font-size: 12px; font-weight: 600; color: var(--text-muted); cursor: pointer; border-radius: 8px; transition: all 0.2s; font-family: 'Urbanist', sans-serif; border: none; background: none; }
.db-pill.active { background: var(--primary); color: white; box-shadow: 0 4px 12px rgba(230,57,70,0.3); }
 
/* SEARCH */
.search-wrap { position: relative; }
.search-wrap i { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--text-muted); font-size: 12px; }
.search-wrap input { width: 100%; height: 40px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); border-radius: 14px; padding-left: 36px; color: var(--text-main); font-family: 'Urbanist', sans-serif; font-size: 13px; outline: none; }
.search-wrap input:focus { border-color: rgba(230,57,70,0.4); }
 
/* CHAT LIST */
.chat-list { display: flex; flex-direction: column; gap: 6px; overflow-y: auto; flex-grow: 1; }
.chat-list::-webkit-scrollbar { width: 3px; }
.chat-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
.chat-item { padding: 11px 13px; border-radius: 12px; background: rgba(255,255,255,0.01); border: 1px solid transparent; font-size: 13px; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: space-between; transition: all 0.2s; }
.chat-item:hover { border-color: rgba(230,57,70,0.2); color: var(--text-main); background: rgba(255,255,255,0.03); }
.chat-item.active { border-color: var(--primary); color: var(--text-main); background: rgba(230,57,70,0.08); }
.chat-item-left { display: flex; align-items: center; gap: 8px; width: 75%; overflow: hidden; }
.chat-title-span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rename-input { background: transparent; border: none; border-bottom: 1px solid var(--primary); color: var(--text-main); font-family: 'Urbanist', sans-serif; font-size: 13px; outline: none; width: 100%; }
.chat-actions { display: flex; gap: 6px; opacity: 0; transition: opacity 0.2s; }
.chat-item:hover .chat-actions { opacity: 0.8; }
.action-icon { color: var(--text-muted); font-size: 11px; cursor: pointer; transition: color 0.2s; background: none; border: none; padding: 2px; }
.action-icon:hover { color: var(--primary); }
.btn-new-chat { background: transparent; border: 1px dashed var(--primary); color: var(--primary); padding: 13px; border-radius: 16px; cursor: pointer; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s; font-family: 'Urbanist', sans-serif; font-size: 13px; }
.btn-new-chat:hover { background: rgba(230,57,70,0.08); box-shadow: 0 4px 12px rgba(230,57,70,0.15); }
 
/* MAIN */
.main {
    flex-grow: 1; display: flex; flex-direction: column;
    background: var(--bg-card); overflow: hidden; position: relative; z-index: 2;
    margin-left: 332px; transition: margin-left 0.35s cubic-bezier(0.25,0.8,0.25,1);
}
.sidebar.collapsed ~ .main { margin-left: 0; }
.header { padding: 18px 36px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: rgba(11,11,13,0.85); backdrop-filter: blur(10px); flex-shrink: 0; }
.header-left { display: flex; align-items: center; gap: 18px; }
.menu-toggle { background: rgba(255,255,255,0.03); border: 1px solid var(--border); color: var(--text-main); width: 38px; height: 38px; border-radius: 12px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; }
.menu-toggle:hover { color: var(--primary); border-color: rgba(230,57,70,0.4); background: rgba(230,57,70,0.05); }
.logo { font-size: 18px; font-weight: 700; letter-spacing: 3px; }
.logo span { color: var(--primary); }
.badge-green { background: rgba(16,185,129,0.15); border: 1px solid #10b981; color: #10b981; padding: 3px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
.header-right { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }
 
/* CHAT SCROLLER */
.chat-scroller { flex-grow: 1; overflow-y: auto; padding: 32px 40px; display: flex; flex-direction: column; gap: 20px; }
.chat-scroller::-webkit-scrollbar { width: 4px; }
.chat-scroller::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 4px; }
 
/* MESSAGES */
.message { display: flex; gap: 12px; max-width: 78%; animation: fadeUp 0.3s cubic-bezier(0.16,1,0.3,1); }
@keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
.message.user { align-self: flex-end; flex-direction: row-reverse; }
.avatar { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; flex-shrink: 0; }
.message.user .avatar { background: var(--primary); color: white; }
.message.bot .avatar { background: #121215; border: 1px solid var(--primary); color: var(--primary); }
.msg-bubble { background: rgba(30,30,40,0.4); border: 1px solid var(--border); padding: 15px 18px; border-radius: 18px; font-size: 14px; line-height: 1.65; flex: 1; }
.message.user .msg-bubble { background: linear-gradient(135deg, #E63946 0%, #B81D24 50%, #820D13 100%); border: 1px solid rgba(255,255,255,0.18); box-shadow: 0 8px 24px rgba(230,57,70,0.3); color: #fff; }
 
/* RESULTS TABLE */
.result-table-wrap { margin-top: 12px; overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
.result-table { width: 100%; border-collapse: collapse; background: rgba(10,10,12,0.6); font-size: 13px; }
.result-table th { text-align: left; color: var(--primary); padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; white-space: nowrap; }
.result-table td { padding: 11px 14px; border-bottom: 1px solid rgba(255,255,255,0.03); color: #e0e0e0; white-space: nowrap; }
.result-table tr:last-child td { border-bottom: none; }
.result-table tr:hover td { background: rgba(230,57,70,0.04); }
 
/* ACTION ROW */
.action-row { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; border-top: 1px solid var(--border); padding-top: 12px; }
.action-btn { background: rgba(255,255,255,0.03); border: 1px solid var(--border); color: #ddd; padding: 7px 14px; border-radius: 8px; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 5px; transition: all 0.2s; font-family: 'Urbanist', sans-serif; font-weight: 600; }
.action-btn:hover { border-color: var(--primary); color: white; background: rgba(230,57,70,0.1); }
.action-btn:disabled { opacity: 0.5; cursor: default; }
 
/* SQL BLOCK */
.sql-block { margin-top: 10px; background: rgba(10,10,12,0.9); border: 1px solid var(--border); border-left: 3px solid var(--primary); border-radius: 10px; padding: 12px 14px; font-family: monospace; font-size: 12px; color: #aaa; white-space: pre-wrap; word-break: break-all; display: none; }
 
/* HOT BUTTONS */
.hot-buttons { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; padding: 0 36px 16px; flex-shrink: 0; }
.hot-btn { background: linear-gradient(135deg, var(--primary), var(--primary-dark)); color: white; border: 1px solid rgba(255,255,255,0.1); padding: 11px 20px; border-radius: 24px; font-weight: 600; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 7px; box-shadow: 0 4px 15px rgba(230,57,70,0.2); transition: all 0.25s; font-family: 'Urbanist', sans-serif; }
.hot-btn:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(230,57,70,0.4); }
 
/* INPUT */
.input-area { padding: 8px 36px 32px; flex-shrink: 0; display: flex; justify-content: center; }
.input-box { width: 100%; max-width: 820px; background: rgba(14,14,18,0.95); border: 1px solid var(--border); height: 54px; border-radius: 28px; display: flex; align-items: center; padding: 0 20px; gap: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); transition: border-color 0.2s; }
.input-box:focus-within { border-color: rgba(230,57,70,0.4); }
.input-box input { flex-grow: 1; background: transparent; border: none; color: white; font-size: 14px; outline: none; font-family: 'Urbanist', sans-serif; }
.btn-send { background: none; border: none; color: var(--primary); font-size: 17px; cursor: pointer; transition: all 0.2s; padding: 4px 8px; }
.btn-send:hover { color: white; transform: scale(1.1); }
 
/* LOADING DOTS */
.dot-flash { display: flex; gap: 5px; align-items: center; padding: 4px 0; }
.dot-flash span { width: 8px; height: 8px; background: var(--primary); border-radius: 50%; animation: blink 1.2s infinite; }
.dot-flash span:nth-child(2) { animation-delay: 0.2s; }
.dot-flash span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,100% { opacity:0.2; } 50% { opacity:1; } }
 
/* TOAST */
.toast { position: fixed; top: 24px; right: 24px; background: #0d2818; border: 1px solid #1e5e2f; color: #4ade80; padding: 12px 22px; border-radius: 12px; font-size: 13px; font-weight: 600; display: none; z-index: 999; box-shadow: 0 10px 25px rgba(0,0,0,0.5); animation: slideDown 0.3s ease; }
@keyframes slideDown { from { transform:translateY(-16px); opacity:0; } to { transform:translateY(0); opacity:1; } }
 
/* CONTRA-ATAQUE */
.attack-block { border-left: 3px solid var(--primary); padding: 12px 16px; background: rgba(230,57,70,0.05); border-radius: 0 12px 12px 0; margin-top: 10px; font-size: 13px; line-height: 1.7; }
</style>
</head>
<body>
<div class="fluid-glow-1"></div>
<div class="fluid-glow-2"></div>
<div class="toast" id="toast">✅ CSV exportado com sucesso!</div>
 
<!-- SIDEBAR -->
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">
        <div class="sidebar-title">Chats &amp; Consultas</div>
        <i class="fa-solid fa-clock-rotate-left" style="opacity:0.4;font-size:13px;"></i>
    </div>
    <div class="db-selector">
        <div class="db-label">Base de Dados Ativa</div>
        <div class="db-pills">
            <button class="db-pill active" onclick="selectDb('todas',this)">Todas</button>
            <button class="db-pill" onclick="selectDb('FarmaPonte',this)">Ponte</button>
            <button class="db-pill" onclick="selectDb('Vera Cruz',this)">Vera Cruz</button>
        </div>
    </div>
    <div class="search-wrap">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input type="text" placeholder="Buscar chats..." oninput="filterChats(this.value)">
    </div>
    <div class="chat-list" id="chatList"></div>
    <button class="btn-new-chat" onclick="newChat()">
        <i class="fa-solid fa-plus"></i> Novo Chat
    </button>
</div>
 
<!-- MAIN -->
<div class="main" id="main">
    <div class="header">
        <div class="header-left">
            <button class="menu-toggle" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="logo">FARMAZZINI <span>INTEL</span></div>
        </div>
        <div class="header-right">
            <span class="badge-green">✨ Bedrock Conectado</span>
            <i class="fa-solid fa-circle" style="color:#10b981;font-size:7px;"></i>
            Base: <span id="dbLabel">Todas</span>
        </div>
    </div>
 
    <div class="chat-scroller" id="chatWindow"></div>
 
    <div class="hot-buttons">
        <button class="hot-btn" onclick="hotTrigger('estoque')"><i class="fa-solid fa-boxes-stacked"></i> Estoque Crítico</button>
        <button class="hot-btn" onclick="hotTrigger('preco')"><i class="fa-solid fa-tags"></i> Achar Mais Barato</button>
        <button class="hot-btn" onclick="hotTrigger('promos')"><i class="fa-solid fa-fire"></i> Maiores Promoções</button>
    </div>
 
    <div class="input-area">
        <div class="input-box">
            <input type="text" id="userInput" placeholder="Faça uma consulta estratégica ao mercado..."
                   onkeypress="if(event.key==='Enter') sendMessage()">
            <button class="btn-send" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    </div>
</div>
 
<script>
// ── Estado global ─────────────────────────────────────────────────────────
let activeDb = 'todas';
let activeChatId = 1;
let searchText = '';
let csvData = '';
 
let chats = [{
    id: 1,
    title: 'Análise de Mercado',
    messages: [{
        sender: 'bot',
        html: `<div style="font-size:14px;line-height:1.7;">
            Olá! Seja bem-vindo ao <strong style="color:#E63946;">Farmazzini Intel 2.0</strong>.<br><br>
            Estou conectado ao <strong>Amazon Bedrock (Claude Haiku 4.5)</strong> e ao banco de dados real da Farmazzini via Athena.<br><br>
            Posso analisar <strong>preços, estoque, promoções e cashback</strong> das farmácias FarmaPonte e Vera Cruz.<br><br>
            Use os atalhos rápidos abaixo ou faça qualquer consulta estratégica!
        </div>`
    }]
}];
 
// ── Sidebar ───────────────────────────────────────────────────────────────
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
}
 
function selectDb(db, el) {
    activeDb = db;
    document.querySelectorAll('.db-pill').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    const labels = {'todas':'Todas','FarmaPonte':'FarmaPonte','Vera Cruz':'Vera Cruz'};
    document.getElementById('dbLabel').textContent = labels[db] || db;
    addBotMessage(`🔄 Filtro alterado para <strong>${labels[db] || db}</strong>. Consultas agora filtradas para esta base.`);
}
 
function filterChats(val) {
    searchText = val.toLowerCase();
    renderChatList();
}
 
function renderChatList() {
    const el = document.getElementById('chatList');
    el.innerHTML = '';
    chats.filter(c => c.title.toLowerCase().includes(searchText)).forEach(c => {
        const div = document.createElement('div');
        div.className = 'chat-item' + (c.id === activeChatId ? ' active' : '');
        div.innerHTML = `
            <div class="chat-item-left" onclick="selectChat(${c.id})">
                <i class="fa-regular fa-comment" style="font-size:12px;flex-shrink:0;"></i>
                <span class="chat-title-span" id="ts-${c.id}" ondblclick="startRename(${c.id})">${c.title}</span>
            </div>
            <div class="chat-actions">
                <button class="action-icon" onclick="startRename(${c.id})" title="Renomear"><i class="fa-solid fa-pen"></i></button>
                <button class="action-icon" onclick="deleteChat(${c.id})" title="Excluir"><i class="fa-solid fa-trash-can"></i></button>
            </div>`;
        el.appendChild(div);
    });
}
 
function startRename(id) {
    const span = document.getElementById('ts-' + id);
    if (!span) return;
    const val = span.textContent;
    span.outerHTML = `<input class="rename-input" id="ri-${id}" value="${val}"
        onblur="finishRename(${id})" onkeypress="if(event.key==='Enter')finishRename(${id})">`;
    const inp = document.getElementById('ri-' + id);
    inp && inp.focus();
}
 
function finishRename(id) {
    const inp = document.getElementById('ri-' + id);
    if (!inp) return;
    const chat = chats.find(c => c.id === id);
    if (chat) chat.title = inp.value.trim() || chat.title;
    renderChatList();
}
 
function selectChat(id) {
    activeChatId = id;
    renderChatList();
    renderChat();
}
 
function deleteChat(id) {
    if (chats.length <= 1) { alert('Mantenha pelo menos um chat ativo!'); return; }
    chats = chats.filter(c => c.id !== id);
    if (activeChatId === id) activeChatId = chats[0].id;
    renderChatList();
    renderChat();
}
 
function newChat() {
    const id = Math.max(...chats.map(c => c.id)) + 1;
    chats.push({
        id, title: `Nova Consulta #${id}`,
        messages: [{ sender: 'bot', html: 'Nova sessão aberta. Faça sua consulta estratégica.' }]
    });
    activeChatId = id;
    renderChatList();
    renderChat();
}
 
// ── Render chat ───────────────────────────────────────────────────────────
function renderChat() {
    const win = document.getElementById('chatWindow');
    win.innerHTML = '';
    const chat = chats.find(c => c.id === activeChatId);
    if (!chat) return;
    chat.messages.forEach(m => {
        const div = document.createElement('div');
        div.className = 'message ' + m.sender;
        div.innerHTML = `
            <div class="avatar">${m.sender === 'user' ? 'PM' : 'FZ'}</div>
            <div class="msg-bubble">${m.html}</div>`;
        win.appendChild(div);
    });
    win.scrollTop = win.scrollHeight;
}
 
function addBotMessage(html) {
    const chat = chats.find(c => c.id === activeChatId);
    if (chat) { chat.messages.push({ sender: 'bot', html }); renderChat(); }
}
 
function addUserMessage(text) {
    const chat = chats.find(c => c.id === activeChatId);
    if (chat) { chat.messages.push({ sender: 'user', html: text }); renderChat(); }
}
 
// ── Loading bubble ────────────────────────────────────────────────────────
let loadingDiv = null;
 
function showLoading(label) {
    const win = document.getElementById('chatWindow');
    loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot';
    loadingDiv.innerHTML = `
        <div class="avatar">FZ</div>
        <div class="msg-bubble" style="display:flex;align-items:center;gap:12px;">
            <span style="font-size:13px;color:var(--text-muted);">${label}</span>
            <div class="dot-flash"><span></span><span></span><span></span></div>
        </div>`;
    win.appendChild(loadingDiv);
    win.scrollTop = win.scrollHeight;
}
 
function replaceLoading(html) {
    if (loadingDiv) { loadingDiv.remove(); loadingDiv = null; }
    addBotMessage(html);
}
 
// ── Construir tabela HTML ─────────────────────────────────────────────────
function buildTable(columns, rows) {
    const ths = columns.map(c => `<th>${c}</th>`).join('');
    const trs = rows.map(r =>
        `<tr>${r.map(v => `<td>${v}</td>`).join('')}</tr>`
    ).join('');
    return `<div class="result-table-wrap">
        <table class="result-table">
            <thead><tr>${ths}</tr></thead>
            <tbody>${trs}</tbody>
        </table>
    </div>`;
}
 
// ── Exportar CSV ──────────────────────────────────────────────────────────
function exportCSV() {
    if (!csvData) return;
    const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'farmazzini_resultado.csv'; a.click();
    URL.revokeObjectURL(url);
    const toast = document.getElementById('toast');
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3000);
}
 
// ── Comunicação com o backend Python via fetch ────────────────────────────
async function callBackend(action, pergunta) {
    const params = new URLSearchParams({
        action,
        pergunta,
        farmacia: activeDb === 'todas' ? '' : activeDb,
    });
    const url = window.location.href.split('?')[0] + '?' + params.toString();
    try {
        const resp = await fetch(url);
        const text = await resp.text();
        // Extrai o JSON da resposta do Streamlit (que pode ter HTML em volta)
        const match = text.match(/\\{[\\s\\S]*\\}/);
        if (match) return JSON.parse(match[0]);
        return { ok: false, error: 'Resposta inválida do servidor.' };
    } catch(e) {
        return { ok: false, error: String(e) };
    }
}
 
// ── Enviar mensagem principal ─────────────────────────────────────────────
async function sendMessage() {
    const inp = document.getElementById('userInput');
    const val = inp.value.trim();
    if (!val) return;
    inp.value = '';
 
    // Auto-renomear chat
    const chat = chats.find(c => c.id === activeChatId);
    if (chat && chat.title.startsWith('Nova Consulta')) {
        chat.title = val.length > 22 ? val.substring(0, 20) + '...' : val;
        renderChatList();
    }
 
    addUserMessage(val);
    showLoading('Claude está gerando o SQL e consultando o Athena...');
 
    const result = await callBackend('query', val);
    let html = '';
 
    if (!result.ok) {
        html = `❌ <strong>Erro:</strong> ${result.error}`;
        if (result.sql) {
            html += `<div class="sql-block" style="display:block;margin-top:8px;">${result.sql}</div>`;
        }
    } else if (result.empty) {
        html = `✅ Consulta executada, mas nenhum registro correspondeu aos filtros.`;
        if (result.sql) html += `<div class="sql-block" style="display:block;margin-top:8px;">${result.sql}</div>`;
    } else {
        csvData = result.csv || '';
        const tableHtml = buildTable(result.columns, result.rows);
        const sqlId = 'sql-' + Date.now();
        html = `✅ <strong>${result.rows.length} registro(s) encontrado(s).</strong>
            ${tableHtml}
            <div class="action-row">
                <button class="action-btn" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block';this.innerHTML=this.innerHTML.includes('Ver')?'<i class=\\"fa-solid fa-code\\"></i> Ocultar SQL':'<i class=\\"fa-solid fa-code\\"></i> Ver SQL'">
                    <i class="fa-solid fa-code"></i> Ver SQL
                </button>
                <div class="sql-block" id="${sqlId}">${result.sql || ''}</div>
                <button class="action-btn" onclick="exportCSV()"><i class="fa-solid fa-file-csv"></i> Exportar CSV</button>
                <button class="action-btn" onclick="requestAttack(this, \`${result.rows.slice(0,5).map(r=>r.join(', ')).join(' | ')}\`)">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> ⚡ Contra-Ataque
                </button>
            </div>`;
    }
 
    replaceLoading(html);
}
 
// ── Contra-ataque ─────────────────────────────────────────────────────────
async function requestAttack(btn, contexto) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analisando...';
    showLoading('✨ Claude gerando estratégia de contra-ataque...');
 
    const result = await callBackend('attack', contexto);
    let html = '';
    if (result.ok) {
        const texto = (result.texto || '').replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = `<div style="border-left:3px solid var(--primary);padding-left:12px;margin-bottom:6px;">
            <strong style="color:var(--primary);">⚡ Contra-Ataque Estratégico:</strong>
        </div>${texto}`;
    } else {
        html = `❌ Erro ao gerar contra-ataque: ${result.error}`;
    }
    replaceLoading(html);
}
 
// ── Hot triggers ──────────────────────────────────────────────────────────
function hotTrigger(type) {
    const map = {
        estoque: 'Quais produtos estão Indisponíveis hoje?',
        preco:   'Qual o produto mais barato disponível por farmácia?',
        promos:  'Liste os 10 produtos com maior desconto padrão disponíveis.',
    };
    const q = map[type] || '';
    if (!q) return;
    document.getElementById('userInput').value = q;
    sendMessage();
}
 
// ── Init ──────────────────────────────────────────────────────────────────
renderChatList();
renderChat();
</script>
</body>
</html>
"""
 
components.html(html_interface, height=800, scrolling=False)
# ==============================================================================
# app.py — Farmazzini Intel 2.0  |  Design refresh (DM Sans + Space Grotesk)
# Projeto Farmazzini | Poli Júnior | Equipe 06
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

# Oculta chrome padrão do Streamlit
st.markdown("""
<style>
#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"] { background: #080809; }
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
    action   = query_params.get("action", "")
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
html_interface = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
/* ── DESIGN TOKENS ── */
:root {
  --red:        #E63946;
  --red-deep:   #8B0000;
  --red-mid:    #B81D24;
  --red-glow:   rgba(230,57,70,0.18);
  --bg:         #080809;
  --surface:    #0e0e10;
  --surface2:   #131316;
  --border:     rgba(255,255,255,0.07);
  --border-red: rgba(230,57,70,0.28);
  --text:       #f0f0f2;
  --muted:      #7a7a85;
  --font-d:     'Space Grotesk', sans-serif;
  --font-b:     'DM Sans', sans-serif;
}

/* ── RESET ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body {
  font-family: var(--font-b);
  background: var(--bg);
  color: var(--text);
  display: flex;
  position: relative;
}

/* ── AMBIENT ORBS ── */
.orb {
  position: fixed; border-radius: 50%;
  pointer-events: none; z-index: 0;
  filter: blur(90px);
}
.orb-1 {
  width: 60vw; height: 60vw; top: -20%; left: 15%;
  background: radial-gradient(circle, rgba(200,20,30,0.20) 0%, rgba(130,0,10,0.05) 55%, transparent 80%);
}
.orb-2 {
  width: 45vw; height: 45vw; bottom: -15%; right: 5%;
  background: radial-gradient(circle, rgba(230,57,70,0.12) 0%, transparent 70%);
}

/* ── SIDEBAR ── */
.sidebar {
  position: fixed;
  top: 14px; left: 14px; bottom: 14px;
  width: 298px;
  background: rgba(10,10,13,0.90);
  backdrop-filter: blur(28px);
  border: 1px solid var(--border);
  border-radius: 22px;
  display: flex; flex-direction: column;
  padding: 22px 16px;
  gap: 14px;
  z-index: 20;
  box-shadow: 0 20px 60px rgba(0,0,0,0.65);
  transition: transform 0.32s cubic-bezier(0.22,1,0.36,1), opacity 0.28s;
}
.sidebar.collapsed { transform: translateX(-326px); opacity: 0; pointer-events: none; }

.sb-head { display: flex; align-items: center; justify-content: space-between; padding: 0 2px; }
.sb-label {
  font-family: var(--font-d);
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 2.5px;
  color: var(--red);
}
.sb-icon { color: var(--muted); font-size: 13px; opacity: 0.6; }

/* DB PILLS */
.db-box {
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px 12px 10px;
  display: flex; flex-direction: column; gap: 8px;
}
.db-box-lbl {
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.5px;
  color: var(--muted);
}
.db-pills {
  display: flex;
  background: rgba(0,0,0,0.50);
  border-radius: 10px; padding: 3px; gap: 2px;
}
.db-pill {
  flex: 1; text-align: center;
  padding: 8px 4px;
  font-family: var(--font-b); font-size: 12px; font-weight: 600;
  color: var(--muted);
  border: none; border-radius: 8px;
  background: none; cursor: pointer;
  transition: all 0.18s;
}
.db-pill.active {
  background: linear-gradient(135deg, var(--red), var(--red-deep));
  color: #fff;
  box-shadow: 0 3px 10px rgba(230,57,70,0.32);
}

/* SEARCH */
.srch { position: relative; }
.srch i { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); color: var(--muted); font-size: 12px; }
.srch input {
  width: 100%; height: 40px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0 14px 0 35px;
  color: var(--text); font-family: var(--font-b); font-size: 13px;
  outline: none; transition: border-color 0.18s;
}
.srch input:focus { border-color: var(--border-red); }
.srch input::placeholder { color: var(--muted); }

/* CHAT LIST */
.chat-list {
  flex: 1; overflow-y: auto;
  display: flex; flex-direction: column; gap: 4px;
  padding-right: 2px;
}
.chat-list::-webkit-scrollbar { width: 3px; }
.chat-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 3px; }

.chat-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px 12px;
  border-radius: 10px; border: 1px solid transparent;
  font-size: 13px; color: var(--muted);
  cursor: pointer; transition: all 0.16s;
}
.chat-item:hover { background: rgba(255,255,255,0.03); border-color: rgba(230,57,70,0.15); color: var(--text); }
.chat-item.active { background: rgba(230,57,70,0.07); border-color: var(--border-red); color: var(--text); }
.ci-left { display: flex; align-items: center; gap: 8px; overflow: hidden; flex: 1; }
.ci-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ci-rename { background: transparent; border: none; border-bottom: 1px solid var(--red); color: var(--text); font-family: var(--font-b); font-size: 13px; outline: none; width: 100%; }
.ci-actions { display: flex; gap: 6px; opacity: 0; transition: opacity 0.14s; flex-shrink: 0; }
.chat-item:hover .ci-actions { opacity: 0.75; }
.ci-btn { background: none; border: none; color: var(--muted); font-size: 11px; cursor: pointer; padding: 2px; transition: color 0.14s; }
.ci-btn:hover { color: var(--red); }

.btn-new {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 13px;
  border-radius: 14px;
  background: transparent;
  border: 1px dashed rgba(230,57,70,0.42);
  color: var(--red);
  font-family: var(--font-b); font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.18s;
}
.btn-new:hover { background: rgba(230,57,70,0.06); box-shadow: 0 4px 14px rgba(230,57,70,0.12); }

/* ── MAIN AREA ── */
.main {
  flex: 1; display: flex; flex-direction: column;
  position: relative; z-index: 2;
  height: 100vh; overflow: hidden;
  background: var(--bg);
  margin-left: 326px;
  transition: margin-left 0.32s cubic-bezier(0.22,1,0.36,1);
}
.sidebar.collapsed ~ .main { margin-left: 0; }

/* HEADER */
.hdr {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 36px;
  border-bottom: 1px solid var(--border);
  background: rgba(8,8,9,0.88);
  backdrop-filter: blur(14px);
  flex-shrink: 0;
}
.hdr-left { display: flex; align-items: center; gap: 16px; }
.hdr-toggle {
  width: 38px; height: 38px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text); font-size: 14px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.18s;
}
.hdr-toggle:hover { border-color: var(--border-red); color: var(--red); background: rgba(230,57,70,0.05); }

.logo {
  font-family: var(--font-d);
  font-size: 18px; font-weight: 700; letter-spacing: 2.5px;
  text-transform: uppercase;
}
.logo em { color: var(--red); font-style: normal; }

.hdr-right { display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--muted); }
.badge-conn {
  background: rgba(16,185,129,0.12);
  border: 1px solid rgba(16,185,129,0.35);
  color: #10b981;
  padding: 3px 10px; border-radius: 5px;
  font-size: 10px; font-weight: 700; text-transform: uppercase;
}
.dot-live { width: 6px; height: 6px; background: #10b981; border-radius: 50%; }

/* SCROLLER */
.scroller {
  flex: 1; overflow-y: auto;
  padding: 30px 40px;
  display: flex; flex-direction: column; gap: 20px;
}
.scroller::-webkit-scrollbar { width: 4px; }
.scroller::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 4px; }

/* MESSAGES */
.msg { display: flex; gap: 12px; max-width: 78%; animation: msgIn 0.28s cubic-bezier(0.16,1,0.3,1); }
@keyframes msgIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
.msg.user { align-self: flex-end; flex-direction: row-reverse; }

.av {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-d); font-size: 12px; font-weight: 700;
  flex-shrink: 0;
}
.msg.user .av { background: linear-gradient(135deg, var(--red), var(--red-deep)); color: #fff; }
.msg.bot  .av { background: var(--surface2); border: 1px solid var(--border-red); color: var(--red); }

.bubble {
  padding: 14px 18px;
  border-radius: 18px; border: 1px solid var(--border);
  background: rgba(18,18,24,0.55);
  font-size: 14px; line-height: 1.68; flex: 1;
}
.msg.user .bubble {
  background: linear-gradient(140deg, #E63946 0%, #C01E27 45%, #7a0b12 100%);
  border-color: rgba(255,255,255,0.15);
  box-shadow: 0 8px 26px rgba(230,57,70,0.28);
  color: #fff;
}

/* RESULTS TABLE */
.tbl-wrap { margin-top: 12px; overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
.tbl { width: 100%; border-collapse: collapse; background: rgba(8,8,10,0.65); font-size: 13px; }
.tbl th { text-align: left; color: var(--red); padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 10px; text-transform: uppercase; letter-spacing: 1px; white-space: nowrap; font-family: var(--font-d); }
.tbl td { padding: 11px 14px; border-bottom: 1px solid rgba(255,255,255,0.03); color: #e0e0e0; white-space: nowrap; }
.tbl tr:last-child td { border-bottom: none; }
.tbl tr:hover td { background: rgba(230,57,70,0.04); }

/* SQL BLOCK */
.sql-blk {
  display: none; margin-top: 10px;
  background: rgba(8,8,10,0.9); border: 1px solid var(--border);
  border-left: 3px solid var(--red);
  border-radius: 10px; padding: 12px 14px;
  font-family: monospace; font-size: 12px; color: #aaa;
  white-space: pre-wrap; word-break: break-all;
}

/* ACTION ROW */
.act-row {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin-top: 14px; padding-top: 12px;
  border-top: 1px solid var(--border);
}
.act-btn {
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  color: #d0d0d0; padding: 7px 14px; border-radius: 8px;
  font-family: var(--font-b); font-size: 12px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; gap: 5px;
  transition: all 0.16s;
}
.act-btn:hover { border-color: var(--red); color: #fff; background: rgba(230,57,70,0.09); }
.act-btn:disabled { opacity: 0.45; cursor: default; }

/* COUNTER ATTACK */
.atk-blk {
  border-left: 3px solid var(--red);
  padding: 12px 16px;
  background: rgba(230,57,70,0.05);
  border-radius: 0 12px 12px 0;
  margin-top: 10px; font-size: 13px; line-height: 1.75;
}

/* HOT BUTTONS */
.hot-row {
  display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
  padding: 0 36px 14px; flex-shrink: 0;
}
.hot-btn {
  background: linear-gradient(135deg, var(--red), var(--red-deep));
  color: #fff; border: 1px solid rgba(255,255,255,0.1);
  padding: 11px 20px; border-radius: 24px;
  font-family: var(--font-b); font-size: 12px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; gap: 7px;
  box-shadow: 0 4px 16px rgba(230,57,70,0.20);
  transition: all 0.22s;
}
.hot-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(230,57,70,0.38); }

/* INPUT */
.inp-area { padding: 0 36px 28px; display: flex; justify-content: center; flex-shrink: 0; }
.inp-box {
  width: 100%; max-width: 820px; height: 54px;
  background: rgba(12,12,15,0.96); border: 1px solid var(--border);
  border-radius: 28px; display: flex; align-items: center;
  padding: 0 20px; gap: 12px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.45);
  transition: border-color 0.18s;
}
.inp-box:focus-within { border-color: rgba(230,57,70,0.38); }
.inp-box input {
  flex: 1; background: transparent; border: none;
  color: var(--text); font-family: var(--font-b); font-size: 14px; outline: none;
}
.inp-box input::placeholder { color: var(--muted); }
.btn-send { background: none; border: none; color: var(--red); font-size: 17px; cursor: pointer; transition: all 0.18s; padding: 4px 8px; }
.btn-send:hover { color: #fff; transform: scale(1.1); }

/* LOADING DOTS */
.dots { display: flex; gap: 5px; align-items: center; padding: 4px 0; }
.dot { width: 7px; height: 7px; background: var(--red); border-radius: 50%; animation: blink 1.2s infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,100%{opacity:0.18;} 50%{opacity:1;} }

/* TOAST */
.toast {
  position: fixed; top: 22px; right: 24px;
  background: #091f10; border: 1px solid #1a5226;
  color: #4ade80; padding: 11px 22px; border-radius: 10px;
  font-size: 13px; font-weight: 600; font-family: var(--font-b);
  display: none; z-index: 999;
  box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  animation: toastIn 0.26s ease;
}
@keyframes toastIn { from{transform:translateY(-14px);opacity:0;} to{transform:translateY(0);opacity:1;} }

/* METRICS BAR */
.metrics {
  display: grid; grid-template-columns: repeat(4,1fr);
  gap: 10px; margin-top: 14px;
}
.metric-card {
  background: rgba(10,10,12,0.80);
  border: 1px solid var(--border);
  border-radius: 12px; padding: 12px 14px;
}
.metric-lbl {
  font-family: var(--font-d);
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1.2px; color: var(--red); margin-bottom: 4px;
}
.metric-val { font-family: var(--font-d); font-size: 18px; font-weight: 700; color: #fff; }

/* RESPONSIVE */
@media (max-width: 768px) {
  .sidebar { top: 60px; left: 8px; right: 8px; bottom: 8px; width: calc(100% - 16px); border-radius: 20px; }
  .sidebar.collapsed { transform: translateX(-110%); }
  .main { margin-left: 0 !important; }
  .hdr { padding: 12px 18px; }
  .scroller { padding: 18px; }
  .hot-row { padding: 0 18px 12px; }
  .inp-area { padding: 0 18px 20px; }
  .msg { max-width: 92%; }
  .metrics { grid-template-columns: repeat(2,1fr); }
}
</style>
</head>
<body>

<!-- AMBIENT ORBS -->
<div class="orb orb-1"></div>
<div class="orb orb-2"></div>
<div class="toast" id="toast">✅ CSV exportado com sucesso!</div>

<!-- ── SIDEBAR ── -->
<div class="sidebar" id="sidebar">
  <div class="sb-head">
    <span class="sb-label">Chats &amp; Consultas</span>
    <i class="fa-solid fa-clock-rotate-left sb-icon"></i>
  </div>

  <div class="db-box">
    <div class="db-box-lbl">Base de Dados Ativa</div>
    <div class="db-pills">
      <button class="db-pill active" onclick="selectDb('todas',this)">Todas</button>
      <button class="db-pill" onclick="selectDb('FarmaPonte',this)">Ponte</button>
      <button class="db-pill" onclick="selectDb('Vera Cruz',this)">Vera Cruz</button>
    </div>
  </div>

  <div class="srch">
    <i class="fa-solid fa-magnifying-glass"></i>
    <input type="text" placeholder="Buscar chats..." oninput="filterChats(this.value)">
  </div>

  <div class="chat-list" id="chatList"></div>

  <button class="btn-new" onclick="newChat()">
    <i class="fa-solid fa-plus"></i> Novo Chat
  </button>
</div>

<!-- ── MAIN ── -->
<div class="main" id="main">

  <!-- Header -->
  <div class="hdr">
    <div class="hdr-left">
      <button class="hdr-toggle" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
      <div class="logo">Farmazzini <em>Intel</em></div>
    </div>
    <div class="hdr-right">
      <span class="badge-conn">✨ Bedrock Ativo</span>
      <div class="dot-live"></div>
      Base: <span id="dbLabel" style="color:var(--text);font-weight:500;">Todas</span>
    </div>
  </div>

  <!-- Messages -->
  <div class="scroller" id="chatWindow"></div>

  <!-- Hot buttons -->
  <div class="hot-row">
    <button class="hot-btn" onclick="hotTrigger('estoque')"><i class="fa-solid fa-boxes-stacked"></i> Estoque Crítico</button>
    <button class="hot-btn" onclick="hotTrigger('preco')"><i class="fa-solid fa-tags"></i> Achar Mais Barato</button>
    <button class="hot-btn" onclick="hotTrigger('promos')"><i class="fa-solid fa-fire"></i> Maiores Promoções</button>
    <button class="hot-btn" onclick="hotTrigger('pix')"><i class="fa-solid fa-pix"></i> Comparar PIX</button>
  </div>

  <!-- Input -->
  <div class="inp-area">
    <div class="inp-box">
      <input type="text" id="userInput"
             placeholder="Faça uma consulta estratégica ao mercado..."
             onkeypress="if(event.key==='Enter') sendMessage()">
      <button class="btn-send" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
  </div>

</div><!-- /.main -->

<script>
// ── Estado ────────────────────────────────────────────────────────────────────
let activeDb = 'todas';
let activeChatId = 1;
let searchText = '';
let csvData = '';

let chats = [{
  id: 1, title: 'Análise de Mercado',
  messages: [{
    sender: 'bot',
    html: `<div style="font-size:14px;line-height:1.75;">
      Olá! Seja bem-vindo ao <strong style="color:#E63946;">Farmazzini Intel 2.0</strong>.<br><br>
      Estou conectado ao <strong>Amazon Bedrock (Claude Haiku 4.5)</strong> e ao banco de dados real via Athena.<br><br>
      Posso analisar <strong>preços, estoque, promoções e cashback</strong> das farmácias FarmaPonte e Vera Cruz.<br><br>
      Use os atalhos rápidos ou faça qualquer consulta estratégica abaixo!
    </div>`
  }]
}];

// ── Sidebar ───────────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

function selectDb(db, el) {
  activeDb = db;
  document.querySelectorAll('.db-pill').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  const lbl = { todas:'Todas', FarmaPonte:'FarmaPonte', 'Vera Cruz':'Vera Cruz' };
  document.getElementById('dbLabel').textContent = lbl[db] || db;
  addBotMsg(`🔄 Filtro alterado para <strong>${lbl[db] || db}</strong>. Consultas agora filtradas para esta base.`);
}

function filterChats(val) {
  searchText = val.toLowerCase();
  renderList();
}

function renderList() {
  const el = document.getElementById('chatList');
  el.innerHTML = '';
  chats.filter(c => c.title.toLowerCase().includes(searchText)).forEach(c => {
    const div = document.createElement('div');
    div.className = 'chat-item' + (c.id === activeChatId ? ' active' : '');
    div.innerHTML = `
      <div class="ci-left" onclick="selectChat(${c.id})">
        <i class="fa-regular fa-comment" style="font-size:11px;flex-shrink:0;"></i>
        <span class="ci-title" id="ct-${c.id}" ondblclick="startRename(${c.id})">${c.title}</span>
      </div>
      <div class="ci-actions">
        <button class="ci-btn" onclick="startRename(${c.id})" title="Renomear"><i class="fa-solid fa-pen"></i></button>
        <button class="ci-btn" onclick="delChat(${c.id})" title="Excluir"><i class="fa-solid fa-trash-can"></i></button>
      </div>`;
    el.appendChild(div);
  });
}

function startRename(id) {
  const s = document.getElementById('ct-' + id);
  if (!s) return;
  const v = s.textContent;
  s.outerHTML = `<input class="ci-rename" id="cr-${id}" value="${v}"
    onblur="finishRename(${id})" onkeypress="if(event.key==='Enter')finishRename(${id})">`;
  const inp = document.getElementById('cr-' + id);
  inp && inp.focus();
}

function finishRename(id) {
  const inp = document.getElementById('cr-' + id);
  if (!inp) return;
  const chat = chats.find(c => c.id === id);
  if (chat) chat.title = inp.value.trim() || chat.title;
  renderList();
}

function selectChat(id) {
  activeChatId = id;
  renderList();
  renderChat();
}

function delChat(id) {
  if (chats.length <= 1) { alert('Mantenha pelo menos um chat ativo!'); return; }
  chats = chats.filter(c => c.id !== id);
  if (activeChatId === id) activeChatId = chats[0].id;
  renderList(); renderChat();
}

function newChat() {
  const id = Math.max(...chats.map(c => c.id)) + 1;
  chats.push({ id, title: `Nova Consulta #${id}`, messages: [
    { sender: 'bot', html: 'Nova sessão aberta. Faça sua consulta estratégica.' }
  ]});
  activeChatId = id;
  renderList(); renderChat();
}

// ── Render chat ───────────────────────────────────────────────────────────────
function renderChat() {
  const win = document.getElementById('chatWindow');
  win.innerHTML = '';
  const chat = chats.find(c => c.id === activeChatId);
  if (!chat) return;
  chat.messages.forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg ' + m.sender;
    div.innerHTML = `<div class="av">${m.sender === 'user' ? 'PM' : 'FZ'}</div>
                     <div class="bubble">${m.html}</div>`;
    win.appendChild(div);
  });
  win.scrollTop = win.scrollHeight;
}

function addBotMsg(html) {
  const chat = chats.find(c => c.id === activeChatId);
  if (chat) { chat.messages.push({ sender:'bot', html }); renderChat(); }
}

function addUserMsg(text) {
  const chat = chats.find(c => c.id === activeChatId);
  if (chat) { chat.messages.push({ sender:'user', html: text }); renderChat(); }
}

// ── Loading ───────────────────────────────────────────────────────────────────
let _ldDiv = null;

function showLoading(label) {
  const win = document.getElementById('chatWindow');
  _ldDiv = document.createElement('div');
  _ldDiv.className = 'msg bot';
  _ldDiv.innerHTML = `
    <div class="av">FZ</div>
    <div class="bubble" style="display:flex;align-items:center;gap:14px;">
      <span style="font-size:13px;color:var(--muted);">${label}</span>
      <div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
    </div>`;
  win.appendChild(_ldDiv);
  win.scrollTop = win.scrollHeight;
}

function replaceLoading(html) {
  if (_ldDiv) { _ldDiv.remove(); _ldDiv = null; }
  addBotMsg(html);
}

// ── Metrics ───────────────────────────────────────────────────────────────────
function buildMetrics(columns, rows) {
  const totalRecs = rows.length;
  const idx = (name) => columns.findIndex(c => c.toLowerCase() === name.toLowerCase());

  const ixOriginal = idx('preco_original');
  const ixPix      = idx('preco_pix');
  const ixDisp     = idx('disponibilidade');
  const ixFarmacia = idx('farmacia');

  let mediaOrig = '—', menorPix = '—', dispCount = '—', farmCount = '—';

  if (ixOriginal >= 0) {
    const vals = rows.map(r => parseFloat(r[ixOriginal])).filter(v => !isNaN(v));
    if (vals.length) mediaOrig = 'R$ ' + (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(2);
  }
  if (ixPix >= 0) {
    const vals = rows.map(r => parseFloat(r[ixPix])).filter(v => !isNaN(v));
    if (vals.length) menorPix = 'R$ ' + Math.min(...vals).toFixed(2);
  }
  if (ixDisp >= 0) {
    dispCount = rows.filter(r => r[ixDisp] === 'Disponível').length;
  }
  if (ixFarmacia >= 0) {
    farmCount = new Set(rows.map(r => r[ixFarmacia])).size;
  }

  return `<div class="metrics">
    <div class="metric-card"><div class="metric-lbl">Registros</div><div class="metric-val">${totalRecs.toLocaleString('pt-BR')}</div></div>
    <div class="metric-card"><div class="metric-lbl">Preço Médio</div><div class="metric-val">${mediaOrig}</div></div>
    <div class="metric-card"><div class="metric-lbl">Menor PIX</div><div class="metric-val">${menorPix}</div></div>
    <div class="metric-card"><div class="metric-lbl">${ixDisp >= 0 ? 'Disponíveis' : 'Farmácias'}</div><div class="metric-val">${ixDisp >= 0 ? dispCount : farmCount}</div></div>
  </div>`;
}

// ── Build table ───────────────────────────────────────────────────────────────
function buildTable(columns, rows) {
  const ths = columns.map(c => `<th>${c}</th>`).join('');
  const trs = rows.map(r => `<tr>${r.map(v => `<td>${v}</td>`).join('')}</tr>`).join('');
  return `<div class="tbl-wrap"><table class="tbl">
    <thead><tr>${ths}</tr></thead>
    <tbody>${trs}</tbody>
  </table></div>`;
}

// ── Export CSV ────────────────────────────────────────────────────────────────
function exportCSV() {
  if (!csvData) return;
  const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'farmazzini_resultado.csv'; a.click();
  URL.revokeObjectURL(url);
  const t = document.getElementById('toast');
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3000);
}

// ── Backend call ──────────────────────────────────────────────────────────────
async function callBackend(action, pergunta) {
  const params = new URLSearchParams({
    action, pergunta,
    farmacia: activeDb === 'todas' ? '' : activeDb,
  });
  const url = window.location.href.split('?')[0] + '?' + params.toString();
  try {
    const resp = await fetch(url);
    const text = await resp.text();
    const match = text.match(/\{[\s\S]*\}/);
    if (match) return JSON.parse(match[0]);
    return { ok: false, error: 'Resposta inválida do servidor.' };
  } catch(e) {
    return { ok: false, error: String(e) };
  }
}

// ── Send message ──────────────────────────────────────────────────────────────
async function sendMessage() {
  const inp = document.getElementById('userInput');
  const val = inp.value.trim();
  if (!val) return;
  inp.value = '';

  const chat = chats.find(c => c.id === activeChatId);
  if (chat && chat.title.startsWith('Nova Consulta')) {
    chat.title = val.length > 22 ? val.substring(0,20) + '…' : val;
    renderList();
  }

  addUserMsg(val);
  showLoading('Claude está gerando o SQL e consultando o Athena…');

  const result = await callBackend('query', val);
  let html = '';

  if (!result.ok) {
    html = `❌ <strong>Erro:</strong> ${result.error}`;
    if (result.sql) html += `<div class="sql-blk" style="display:block;margin-top:8px;">${result.sql}</div>`;

  } else if (result.empty) {
    html = `✅ Consulta executada, mas nenhum registro correspondeu aos filtros.`;
    if (result.sql) html += `<div class="sql-blk" style="display:block;margin-top:8px;">${result.sql}</div>`;

  } else {
    csvData = result.csv || '';
    const metricsHtml = buildMetrics(result.columns, result.rows);
    const tableHtml   = buildTable(result.columns, result.rows);
    const sqlId       = 'sql-' + Date.now();
    const ctx         = result.rows.slice(0,5).map(r => r.join(', ')).join(' | ').replace(/`/g,"'");

    html = `✅ <strong>${result.rows.length} registro(s) encontrado(s).</strong>
      ${metricsHtml}
      ${tableHtml}
      <div class="act-row">
        <button class="act-btn" onclick="toggleSql('${sqlId}',this)">
          <i class="fa-solid fa-code"></i> Ver SQL
        </button>
        <div class="sql-blk" id="${sqlId}">${(result.sql || '').replace(/</g,'&lt;')}</div>
        <button class="act-btn" onclick="exportCSV()"><i class="fa-solid fa-file-csv"></i> Exportar CSV</button>
        <button class="act-btn" onclick="requestAttack(this,'${ctx}')">
          <i class="fa-solid fa-wand-magic-sparkles"></i> ⚡ Contra-Ataque
        </button>
      </div>`;
  }

  replaceLoading(html);
}

function toggleSql(id, btn) {
  const el = document.getElementById(id);
  if (!el) return;
  const show = el.style.display !== 'block';
  el.style.display = show ? 'block' : 'none';
  btn.innerHTML = show
    ? '<i class="fa-solid fa-code"></i> Ocultar SQL'
    : '<i class="fa-solid fa-code"></i> Ver SQL';
}

// ── Contra-ataque ─────────────────────────────────────────────────────────────
async function requestAttack(btn, contexto) {
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analisando…';
  showLoading('✨ Claude gerando estratégia de contra-ataque…');

  const result = await callBackend('attack', contexto);
  let html = '';
  if (result.ok) {
    const texto = (result.texto || '')
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = `<div class="atk-blk">
      <strong style="color:var(--red);display:block;margin-bottom:8px;">
        <i class="fa-solid fa-wand-magic-sparkles"></i> Contra-Ataque Estratégico:
      </strong>
      ${texto}
    </div>`;
  } else {
    html = `❌ Erro ao gerar contra-ataque: ${result.error}`;
  }
  replaceLoading(html);
}

// ── Hot triggers ──────────────────────────────────────────────────────────────
function hotTrigger(type) {
  const map = {
    estoque: 'Quais produtos estão Indisponíveis hoje nas farmácias?',
    preco:   'Qual o produto mais barato disponível por farmácia?',
    promos:  'Liste os 10 produtos com maior desconto padrão disponíveis.',
    pix:     'Compare os preços PIX médios entre FarmaPonte e Vera Cruz.',
  };
  const q = map[type];
  if (!q) return;
  document.getElementById('userInput').value = q;
  sendMessage();
}

// ── Init ──────────────────────────────────────────────────────────────────────
renderList();
renderChat();
</script>
</body>
</html>
"""

components.html(html_interface, height=820, scrolling=False)
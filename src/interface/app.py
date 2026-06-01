# ==============================================================================
# app.py — Farmazzini Intel 2.0  |  Design original + backend nativo Streamlit
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import sys, os, json, time, re, uuid
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

st.set_page_config(
    page_title="Farmazzini Intel",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Remove TODO o chrome do Streamlit e deixa só o iframe
st.markdown("""
<style>
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stBottom"] { visibility: hidden !important; display: none !important; }
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.main, .block-container {
    padding: 0 !important; margin: 0 !important;
    background: #080809 !important;
    max-width: 100vw !important; width: 100vw !important;
    overflow: hidden !important;
}
iframe { border: none !important; display: block !important; }
/* Esconde label e borda do text_input nativo */
[data-testid="stTextInput"] {
    position: fixed !important; bottom: 38px !important;
    left: 50% !important; transform: translateX(-50%) !important;
    width: min(820px, calc(100vw - 380px)) !important;
    z-index: 9999 !important; opacity: 0 !important; pointer-events: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── Credenciais AWS ────────────────────────────────────────────────────────────
os.environ["AWS_ACCESS_KEY_ID"]     = st.secrets.get("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_DEFAULT_REGION"]    = st.secrets.get("AWS_DEFAULT_REGION", "us-east-2")

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
3. Colunas: ean, nome, marca, preco_original, preco_pix, preco_cartao, desconto_padrao,
   promocoes_especiais, porcentagem_de_cashback, gtin, disponibilidade
4. Valores exatos de disponibilidade: 'Disponível' ou 'Indisponível'
5. Partições OBRIGATÓRIAS: farmacia, ano, mes, dia
6. farmacia OBRIGATÓRIO em TODA query. Se não especificado: farmacia IN ('FarmaPonte', 'Vera Cruz')
7. Se não especificar data: ano='2026' AND mes='05' AND dia='26'
8. Valores exatos de farmacia: 'FarmaPonte' ou 'Vera Cruz'
9. Para busca por nome: LOWER(nome) LIKE '%termo%'
10. LIMIT apenas quando pedir número específico.
11. Para ordenar desconto: TRY_CAST(REPLACE(desconto_padrao,'%','') AS DOUBLE)
12. SEMPRE inclua farmacia e nome no SELECT
Pergunta: {user_prompt}"""

# ── AWS helpers ────────────────────────────────────────────────────────────────
def gerar_sql(prompt, farmacia_filtro=None):
    client = boto3.client("bedrock-runtime", region_name=REGION)
    p = f"{prompt} (considere apenas farmacia='{farmacia_filtro}')" if farmacia_filtro else prompt
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31", "max_tokens": 800,
        "messages": [{"role": "user", "content": SQL_PROMPT.replace("{user_prompt}", p)}],
    })
    try:
        r = client.invoke_model(modelId=MODEL_ID, body=body)
        return json.loads(r["body"].read())["content"][0]["text"].strip(), None
    except Exception as e:
        return "", str(e)

def executar_sql(sql):
    client = boto3.client("stepfunctions", region_name=REGION)
    try:
        exec_resp = client.start_execution(stateMachineArn=STATE_MACHINE, input=json.dumps({"query": sql}))
        arn = exec_resp["executionArn"]
        while True:
            resp = client.describe_execution(executionArn=arn)
            if resp["status"] in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"): break
            time.sleep(1)
        return resp["status"], None, resp
    except Exception as e:
        return "FAILED", str(e), {}

def buscar_s3(status_resp):
    client = boto3.client("s3", region_name=REGION)
    try:
        output = json.loads(status_resp.get("output", "{}"))
        qid = output.get("QueryExecution", {}).get("QueryExecutionId")
        if not qid: return None, "QueryExecutionId não encontrado."
        time.sleep(1.5)
        obj = client.get_object(Bucket=BUCKET, Key=f"{PREFIXO}{qid}.csv")
        return pd.read_csv(StringIO(obj["Body"].read().decode("utf-8"))), None
    except Exception as e:
        return None, str(e)

def gerar_contra_ataque(resumo):
    client = boto3.client("bedrock-runtime", region_name=REGION)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31", "max_tokens": 600,
        "messages": [{"role": "user", "content": (
            f"Com base nestes dados de mercado farmacêutico:\n{resumo}\n\n"
            "Gere 2 planos de ação rápidos e práticos de marketing ou precificação "
            "para a Farmazzini contra-atacar e preservar sua margem de lucro. "
            "Seja direto, executivo e focado em táticas reais. Use ** para negrito."
        )}],
    })
    try:
        r = client.invoke_model(modelId=MODEL_ID, body=body)
        return json.loads(r["body"].read())["content"][0]["text"].strip()
    except Exception as e:
        return f"Erro: {e}"

# ── Session state ──────────────────────────────────────────────────────────────
def _init():
    if "chats" not in st.session_state:
        pid = str(uuid.uuid4())[:8]
        st.session_state.chats = {pid: {"nome": "Análise de Mercado", "historico": []}}
        st.session_state.chat_ativo = pid
    for k, v in [("chat_ativo", None), ("farmacia_filtro", None),
                  ("pending_query", ""), ("processing", False)]:
        if k not in st.session_state:
            st.session_state[k] = v
_init()

def chat_atual():
    return st.session_state.chats[st.session_state.chat_ativo]

def processar_pergunta(pergunta):
    chat = chat_atual()
    if not chat["historico"] and chat["nome"] == "Análise de Mercado":
        pass  # keep default name for first chat
    chat["historico"].append({"role": "user", "content": pergunta})

    farmacia = st.session_state.farmacia_filtro
    sql, erro = gerar_sql(pergunta, farmacia)
    if erro:
        chat["historico"].append({"role": "bot", "type": "error", "content": f"Erro Bedrock: {erro}"})
        return

    status, erro2, status_resp = executar_sql(sql)
    if erro2 or status != "SUCCEEDED":
        chat["historico"].append({"role": "bot", "type": "error", "content": erro2 or f"Status: {status}", "sql": sql})
        return

    df, erro3 = buscar_s3(status_resp)
    if erro3:
        chat["historico"].append({"role": "bot", "type": "error", "content": f"Erro S3: {erro3}", "sql": sql})
        return

    if df is None or df.empty:
        chat["historico"].append({"role": "bot", "type": "empty", "sql": sql})
    else:
        chat["historico"].append({"role": "bot", "type": "result",
                                   "df_cols": df.columns.tolist(),
                                   "df_rows": df.fillna("—").values.tolist(),
                                   "csv": df.to_csv(index=False),
                                   "sql": sql})

# ── Processar pergunta pendente ────────────────────────────────────────────────
if st.session_state.pending_query:
    pergunta = st.session_state.pending_query
    st.session_state.pending_query = ""
    with st.spinner(f"🧠 Processando: {pergunta[:50]}…"):
        processar_pergunta(pergunta)
    st.rerun()

# ── Construir HTML do histórico ────────────────────────────────────────────────
def build_history_html():
    chat = chat_atual()
    if not chat["historico"]:
        return """<div class="msg bot"><div class="av">FZ</div><div class="bubble">
            Olá! Seja bem-vindo ao <strong style="color:#E63946;">Farmazzini Intel 2.0</strong>.<br><br>
            Estou conectado ao <strong>Amazon Bedrock (Claude Haiku 4.5)</strong> e ao Athena.<br><br>
            Posso analisar <strong>preços, estoque, promoções e cashback</strong> das farmácias.<br><br>
            Use os atalhos rápidos ou faça uma consulta abaixo!
        </div></div>"""

    html = ""
    for msg in chat["historico"]:
        if msg["role"] == "user":
            html += f'<div class="msg user"><div class="av">PM</div><div class="bubble">{msg["content"]}</div></div>'
        else:
            t = msg.get("type", "error")
            if t == "error":
                inner = f'❌ <strong>Erro:</strong> {msg["content"]}'
                if msg.get("sql"):
                    inner += f'<div class="sql-blk" style="display:block;margin-top:8px;">{msg["sql"]}</div>'
                html += f'<div class="msg bot"><div class="av">FZ</div><div class="bubble">{inner}</div></div>'
            elif t == "empty":
                inner = "✅ Consulta executada — nenhum registro correspondeu aos filtros."
                if msg.get("sql"):
                    inner += f'<div class="sql-blk" style="display:block;margin-top:8px;">{msg["sql"]}</div>'
                html += f'<div class="msg bot"><div class="av">FZ</div><div class="bubble">{inner}</div></div>'
            elif t == "result":
                cols = msg["df_cols"]
                rows = msg["df_rows"]
                csv  = msg.get("csv", "")
                sql  = msg.get("sql", "")

                # Metrics
                def get_idx(name):
                    for i, c in enumerate(cols):
                        if c.lower() == name.lower(): return i
                    return -1
                total = len(rows)
                media_orig = "—"; menor_pix = "—"; disp_count = "—"; farm_count = "—"
                ix = get_idx("preco_original")
                if ix >= 0:
                    vals = [float(r[ix]) for r in rows if str(r[ix]).replace(".","").replace("-","").isdigit()]
                    if vals: media_orig = f"R$ {sum(vals)/len(vals):,.2f}"
                ix = get_idx("preco_pix")
                if ix >= 0:
                    vals = [float(r[ix]) for r in rows if str(r[ix]).replace(".","").replace("-","").isdigit()]
                    if vals: menor_pix = f"R$ {min(vals):,.2f}"
                ix = get_idx("disponibilidade")
                if ix >= 0: disp_count = str(sum(1 for r in rows if r[ix] == "Disponível"))
                ix = get_idx("farmacia")
                if ix >= 0: farm_count = str(len(set(r[ix] for r in rows)))

                lbl4 = "Disponíveis" if get_idx("disponibilidade") >= 0 else "Farmácias"
                val4 = disp_count if get_idx("disponibilidade") >= 0 else farm_count

                metrics_html = f"""<div class="metrics">
                  <div class="metric-card"><div class="metric-lbl">Registros</div><div class="metric-val">{total:,}</div></div>
                  <div class="metric-card"><div class="metric-lbl">Preço Médio</div><div class="metric-val">{media_orig}</div></div>
                  <div class="metric-card"><div class="metric-lbl">Menor PIX</div><div class="metric-val">{menor_pix}</div></div>
                  <div class="metric-card"><div class="metric-lbl">{lbl4}</div><div class="metric-val">{val4}</div></div>
                </div>"""

                # Table
                ths = "".join(f"<th>{c}</th>" for c in cols)
                trs = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in rows[:50])
                note = f"<small style='color:#555;font-size:11px;'>Exibindo 50 de {total}</small>" if total > 50 else ""
                table_html = f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div>{note}'

                sql_id = f"sql-{abs(hash(sql)) % 99999}"
                csv_escaped = csv.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

                inner = f"""✅ <strong>{total:,} registro(s) encontrado(s).</strong>
                {metrics_html}
                {table_html}
                <div class="act-row">
                  <button class="act-btn" onclick="toggleSql('{sql_id}',this)">
                    <i class="fa-solid fa-code"></i> Ver SQL
                  </button>
                  <div class="sql-blk" id="{sql_id}">{sql.replace('<','&lt;')}</div>
                  <button class="act-btn" onclick="downloadCSV(`{csv_escaped}`)">
                    <i class="fa-solid fa-file-csv"></i> Exportar CSV
                  </button>
                </div>"""
                html += f'<div class="msg bot"><div class="av">FZ</div><div class="bubble">{inner}</div></div>'
    return html

# ── Construir lista de chats ───────────────────────────────────────────────────
def build_chats_html():
    html = ""
    for cid, c in st.session_state.chats.items():
        ativo = "active" if cid == st.session_state.chat_ativo else ""
        nome = c["nome"][:28]
        html += f"""<div class="chat-item {ativo}" onclick="selectChat('{cid}')">
          <div class="ci-left">
            <i class="fa-regular fa-comment" style="font-size:11px;flex-shrink:0;"></i>
            <span class="ci-title">{nome}</span>
          </div>
        </div>"""
    return html

# ── Render full HTML ──────────────────────────────────────────────────────────
history_html = build_history_html()
chats_html   = build_chats_html()
db_label     = st.session_state.farmacia_filtro or "Todas"

farmaponte_active = "active" if st.session_state.farmacia_filtro == "FarmaPonte" else ""
veracruz_active   = "active" if st.session_state.farmacia_filtro == "Vera Cruz" else ""
todas_active      = "active" if not st.session_state.farmacia_filtro else ""

html_page = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
:root {{
  --red:#E63946; --red-deep:#8B0000; --red-mid:#B81D24;
  --bg:#080809; --surface:#0e0e10; --surface2:#131316;
  --border:rgba(255,255,255,0.07); --border-red:rgba(230,57,70,0.28);
  --text:#f0f0f2; --muted:#7a7a85;
  --font-d:'Space Grotesk',sans-serif; --font-b:'DM Sans',sans-serif;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{height:100%;overflow:hidden;}}
body{{font-family:var(--font-b);background:var(--bg);color:var(--text);display:flex;position:relative;}}

.orb{{position:fixed;border-radius:50%;pointer-events:none;z-index:0;filter:blur(90px);}}
.orb-1{{width:60vw;height:60vw;top:-20%;left:15%;background:radial-gradient(circle,rgba(200,20,30,0.20) 0%,rgba(130,0,10,0.05) 55%,transparent 80%);}}
.orb-2{{width:45vw;height:45vw;bottom:-15%;right:5%;background:radial-gradient(circle,rgba(230,57,70,0.12) 0%,transparent 70%);}}

.sidebar{{position:fixed;top:14px;left:14px;bottom:14px;width:298px;background:rgba(10,10,13,0.90);backdrop-filter:blur(28px);border:1px solid var(--border);border-radius:22px;display:flex;flex-direction:column;padding:22px 16px;gap:14px;z-index:20;box-shadow:0 20px 60px rgba(0,0,0,0.65);transition:transform 0.32s cubic-bezier(0.22,1,0.36,1),opacity 0.28s;}}
.sidebar.collapsed{{transform:translateX(-326px);opacity:0;pointer-events:none;}}
.sb-head{{display:flex;align-items:center;justify-content:space-between;padding:0 2px;}}
.sb-label{{font-family:var(--font-d);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:2.5px;color:var(--red);}}

.db-box{{background:rgba(255,255,255,0.025);border:1px solid var(--border);border-radius:14px;padding:12px 12px 10px;display:flex;flex-direction:column;gap:8px;}}
.db-box-lbl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);}}
.db-pills{{display:flex;background:rgba(0,0,0,0.50);border-radius:10px;padding:3px;gap:2px;}}
.db-pill{{flex:1;text-align:center;padding:8px 4px;font-family:var(--font-b);font-size:12px;font-weight:600;color:var(--muted);border:none;border-radius:8px;background:none;cursor:pointer;transition:all 0.18s;}}
.db-pill.active{{background:linear-gradient(135deg,var(--red),var(--red-deep));color:#fff;box-shadow:0 3px 10px rgba(230,57,70,0.32);}}

.srch{{position:relative;}}
.srch i{{position:absolute;left:13px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:12px;}}
.srch input{{width:100%;height:40px;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:12px;padding:0 14px 0 35px;color:var(--text);font-family:var(--font-b);font-size:13px;outline:none;transition:border-color 0.18s;}}
.srch input:focus{{border-color:var(--border-red);}}
.srch input::placeholder{{color:var(--muted);}}

.chat-list{{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:4px;padding-right:2px;}}
.chat-list::-webkit-scrollbar{{width:3px;}}
.chat-list::-webkit-scrollbar-thumb{{background:rgba(255,255,255,0.07);border-radius:3px;}}
.chat-item{{display:flex;align-items:center;justify-content:space-between;padding:11px 12px;border-radius:10px;border:1px solid transparent;font-size:13px;color:var(--muted);cursor:pointer;transition:all 0.16s;}}
.chat-item:hover{{background:rgba(255,255,255,0.03);border-color:rgba(230,57,70,0.15);color:var(--text);}}
.chat-item.active{{background:rgba(230,57,70,0.07);border-color:var(--border-red);color:var(--text);}}
.ci-left{{display:flex;align-items:center;gap:8px;overflow:hidden;flex:1;}}
.ci-title{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}

.btn-new{{display:flex;align-items:center;justify-content:center;gap:8px;padding:13px;border-radius:14px;background:transparent;border:1px dashed rgba(230,57,70,0.42);color:var(--red);font-family:var(--font-b);font-size:13px;font-weight:600;cursor:pointer;transition:all 0.18s;}}
.btn-new:hover{{background:rgba(230,57,70,0.06);box-shadow:0 4px 14px rgba(230,57,70,0.12);}}

.main{{flex:1;display:flex;flex-direction:column;position:relative;z-index:2;height:100vh;overflow:hidden;background:var(--bg);margin-left:326px;transition:margin-left 0.32s cubic-bezier(0.22,1,0.36,1);}}
.sidebar.collapsed ~ .main{{margin-left:0;}}

.hdr{{display:flex;align-items:center;justify-content:space-between;padding:16px 36px;border-bottom:1px solid var(--border);background:rgba(8,8,9,0.88);backdrop-filter:blur(14px);flex-shrink:0;}}
.hdr-left{{display:flex;align-items:center;gap:16px;}}
.hdr-toggle{{width:38px;height:38px;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.18s;}}
.hdr-toggle:hover{{border-color:var(--border-red);color:var(--red);background:rgba(230,57,70,0.05);}}
.logo{{font-family:var(--font-d);font-size:18px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;}}
.logo em{{color:var(--red);font-style:normal;}}
.hdr-right{{display:flex;align-items:center;gap:10px;font-size:12px;color:var(--muted);}}
.badge-conn{{background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.35);color:#10b981;padding:3px 10px;border-radius:5px;font-size:10px;font-weight:700;text-transform:uppercase;}}
.dot-live{{width:6px;height:6px;background:#10b981;border-radius:50%;}}

.scroller{{flex:1;overflow-y:auto;padding:30px 40px;display:flex;flex-direction:column;gap:20px;}}
.scroller::-webkit-scrollbar{{width:4px;}}
.scroller::-webkit-scrollbar-thumb{{background:rgba(255,255,255,0.06);border-radius:4px;}}

.msg{{display:flex;gap:12px;max-width:82%;animation:msgIn 0.28s cubic-bezier(0.16,1,0.3,1);}}
@keyframes msgIn{{from{{opacity:0;transform:translateY(10px);}}to{{opacity:1;transform:translateY(0);}}}}
.msg.user{{align-self:flex-end;flex-direction:row-reverse;}}
.av{{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-family:var(--font-d);font-size:12px;font-weight:700;flex-shrink:0;}}
.msg.user .av{{background:linear-gradient(135deg,var(--red),var(--red-deep));color:#fff;}}
.msg.bot .av{{background:var(--surface2);border:1px solid var(--border-red);color:var(--red);}}
.bubble{{padding:14px 18px;border-radius:18px;border:1px solid var(--border);background:rgba(18,18,24,0.55);font-size:14px;line-height:1.68;flex:1;}}
.msg.user .bubble{{background:linear-gradient(140deg,#E63946 0%,#C01E27 45%,#7a0b12 100%);border-color:rgba(255,255,255,0.15);box-shadow:0 8px 26px rgba(230,57,70,0.28);color:#fff;}}

.tbl-wrap{{margin-top:12px;overflow-x:auto;border-radius:12px;border:1px solid var(--border);}}
.tbl{{width:100%;border-collapse:collapse;background:rgba(8,8,10,0.65);font-size:13px;}}
.tbl th{{text-align:left;color:var(--red);padding:12px 14px;border-bottom:1px solid var(--border);font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;font-family:var(--font-d);}}
.tbl td{{padding:11px 14px;border-bottom:1px solid rgba(255,255,255,0.03);color:#e0e0e0;white-space:nowrap;}}
.tbl tr:last-child td{{border-bottom:none;}}
.tbl tr:hover td{{background:rgba(230,57,70,0.04);}}

.sql-blk{{display:none;margin-top:10px;background:rgba(8,8,10,0.9);border:1px solid var(--border);border-left:3px solid var(--red);border-radius:10px;padding:12px 14px;font-family:monospace;font-size:12px;color:#aaa;white-space:pre-wrap;word-break:break-all;}}
.act-row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px solid var(--border);}}
.act-btn{{background:rgba(255,255,255,0.03);border:1px solid var(--border);color:#d0d0d0;padding:7px 14px;border-radius:8px;font-family:var(--font-b);font-size:12px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:5px;transition:all 0.16s;}}
.act-btn:hover{{border-color:var(--red);color:#fff;background:rgba(230,57,70,0.09);}}

.hot-row{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;padding:0 36px 14px;flex-shrink:0;}}
.hot-btn{{background:linear-gradient(135deg,var(--red),var(--red-deep));color:#fff;border:1px solid rgba(255,255,255,0.1);padding:11px 20px;border-radius:24px;font-family:var(--font-b);font-size:12px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:7px;box-shadow:0 4px 16px rgba(230,57,70,0.20);transition:all 0.22s;}}
.hot-btn:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(230,57,70,0.38);}}

.inp-area{{padding:0 36px 28px;display:flex;justify-content:center;flex-shrink:0;}}
.inp-box{{width:100%;max-width:820px;height:54px;background:rgba(12,12,15,0.96);border:1px solid var(--border);border-radius:28px;display:flex;align-items:center;padding:0 20px;gap:12px;box-shadow:0 10px 30px rgba(0,0,0,0.45);transition:border-color 0.18s;}}
.inp-box:focus-within{{border-color:rgba(230,57,70,0.38);}}
.inp-box input{{flex:1;background:transparent;border:none;color:var(--text);font-family:var(--font-b);font-size:14px;outline:none;}}
.inp-box input::placeholder{{color:var(--muted);}}
.btn-send{{background:none;border:none;color:var(--red);font-size:17px;cursor:pointer;transition:all 0.18s;padding:4px 8px;}}
.btn-send:hover{{color:#fff;transform:scale(1.1);}}

.dots{{display:flex;gap:5px;align-items:center;padding:4px 0;}}
.dot{{width:7px;height:7px;background:var(--red);border-radius:50%;animation:blink 1.2s infinite;}}
.dot:nth-child(2){{animation-delay:0.2s;}}
.dot:nth-child(3){{animation-delay:0.4s;}}
@keyframes blink{{0%,100%{{opacity:0.18;}}50%{{opacity:1;}}}}

.toast{{position:fixed;top:22px;right:24px;background:#091f10;border:1px solid #1a5226;color:#4ade80;padding:11px 22px;border-radius:10px;font-size:13px;font-weight:600;display:none;z-index:999;}}

.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px;}}
.metric-card{{background:rgba(10,10,12,0.80);border:1px solid var(--border);border-radius:12px;padding:12px 14px;}}
.metric-lbl{{font-family:var(--font-d);font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;color:var(--red);margin-bottom:4px;}}
.metric-val{{font-family:var(--font-d);font-size:18px;font-weight:700;color:#fff;}}

@media(max-width:768px){{
  .sidebar{{top:60px;left:8px;right:8px;bottom:8px;width:calc(100% - 16px);border-radius:20px;}}
  .sidebar.collapsed{{transform:translateX(-110%);}}
  .main{{margin-left:0 !important;}}
  .hdr{{padding:12px 18px;}}
  .scroller{{padding:18px;}}
  .hot-row{{padding:0 18px 12px;}}
  .inp-area{{padding:0 18px 20px;}}
  .msg{{max-width:92%;}}
  .metrics{{grid-template-columns:repeat(2,1fr);}}
}}
</style>
</head>
<body>
<div class="orb orb-1"></div>
<div class="orb orb-2"></div>
<div class="toast" id="toast">✅ CSV exportado!</div>

<div class="sidebar" id="sidebar">
  <div class="sb-head">
    <span class="sb-label">Chats &amp; Consultas</span>
    <i class="fa-solid fa-clock-rotate-left" style="color:var(--muted);font-size:13px;opacity:0.6;"></i>
  </div>
  <div class="db-box">
    <div class="db-box-lbl">Base de Dados Ativa</div>
    <div class="db-pills">
      <button class="db-pill {todas_active}"     onclick="setDb('')">Todas</button>
      <button class="db-pill {farmaponte_active}" onclick="setDb('FarmaPonte')">Ponte</button>
      <button class="db-pill {veracruz_active}"  onclick="setDb('Vera Cruz')">Vera Cruz</button>
    </div>
  </div>
  <div class="srch">
    <i class="fa-solid fa-magnifying-glass"></i>
    <input type="text" placeholder="Buscar chats..." oninput="filterChats(this.value)">
  </div>
  <div class="chat-list" id="chatList">{chats_html}</div>
  <button class="btn-new" onclick="newChat()">
    <i class="fa-solid fa-plus"></i> Novo Chat
  </button>
</div>

<div class="main" id="main">
  <div class="hdr">
    <div class="hdr-left">
      <button class="hdr-toggle" onclick="document.getElementById('sidebar').classList.toggle('collapsed')">
        <i class="fa-solid fa-bars"></i>
      </button>
      <div class="logo">Farmazzini <em>Intel</em></div>
    </div>
    <div class="hdr-right">
      <span class="badge-conn">✨ Bedrock Ativo</span>
      <div class="dot-live"></div>
      Base: <span style="color:var(--text);font-weight:500;">{db_label}</span>
    </div>
  </div>

  <div class="scroller" id="chatWindow">{history_html}</div>

  <div class="hot-row">
    <button class="hot-btn" onclick="send('Quais produtos estão Indisponíveis hoje nas farmácias?')"><i class="fa-solid fa-boxes-stacked"></i> Estoque Crítico</button>
    <button class="hot-btn" onclick="send('Qual o produto mais barato disponível por farmácia?')"><i class="fa-solid fa-tags"></i> Achar Mais Barato</button>
    <button class="hot-btn" onclick="send('Liste os 10 produtos com maior desconto padrão disponíveis.')"><i class="fa-solid fa-fire"></i> Maiores Promoções</button>
    <button class="hot-btn" onclick="send('Compare os preços PIX médios entre FarmaPonte e Vera Cruz.')"><i class="fa-solid fa-pix"></i> Comparar PIX</button>
  </div>

  <div class="inp-area">
    <div class="inp-box">
      <input type="text" id="userInput"
             placeholder="Faça uma consulta estratégica ao mercado..."
             onkeypress="if(event.key==='Enter') send(this.value)">
      <button class="btn-send" onclick="send(document.getElementById('userInput').value)">
        <i class="fa-solid fa-paper-plane"></i>
      </button>
    </div>
  </div>
</div>

<script>
function toggleSql(id, btn) {{
  const el = document.getElementById(id);
  if (!el) return;
  const show = el.style.display !== 'block';
  el.style.display = show ? 'block' : 'none';
  btn.innerHTML = show ? '<i class="fa-solid fa-code"></i> Ocultar SQL' : '<i class="fa-solid fa-code"></i> Ver SQL';
}}

function downloadCSV(data) {{
  const blob = new Blob([data], {{type:'text/csv;charset=utf-8;'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'farmazzini.csv'; a.click();
  URL.revokeObjectURL(url);
  const t = document.getElementById('toast');
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 2500);
}}

function scrollBottom() {{
  const w = document.getElementById('chatWindow');
  if (w) w.scrollTop = w.scrollHeight;
}}

// Comunica com o Streamlit pai via postMessage
function sendToStreamlit(type, value) {{
  window.parent.postMessage({{type: 'streamlit:setComponentValue', value: {{type, value}}}}, '*');
}}

function send(text) {{
  if (!text || !text.trim()) return;
  document.getElementById('userInput').value = '';
  // Mostra mensagem do usuário imediatamente
  const win = document.getElementById('chatWindow');
  const div = document.createElement('div');
  div.className = 'msg user';
  div.innerHTML = `<div class="av">PM</div><div class="bubble">${{text}}</div>`;
  win.appendChild(div);
  // Loading
  const ld = document.createElement('div');
  ld.className = 'msg bot'; ld.id = 'loading-msg';
  ld.innerHTML = `<div class="av">FZ</div><div class="bubble" style="display:flex;align-items:center;gap:14px;">
    <span style="font-size:13px;color:var(--muted);">Claude está gerando o SQL e consultando o Athena…</span>
    <div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
  </div>`;
  win.appendChild(ld);
  scrollBottom();
  sendToStreamlit('query', text);
}}

function setDb(farmacia) {{
  sendToStreamlit('setDb', farmacia);
}}

function newChat() {{
  sendToStreamlit('newChat', '');
}}

function selectChat(id) {{
  sendToStreamlit('selectChat', id);
}}

function filterChats(val) {{
  document.querySelectorAll('.chat-item').forEach(el => {{
    const title = el.querySelector('.ci-title')?.textContent?.toLowerCase() || '';
    el.style.display = title.includes(val.toLowerCase()) ? '' : 'none';
  }});
}}

// Scroll ao carregar
window.addEventListener('load', scrollBottom);
</script>
</body>
</html>"""

# ── Render o HTML ──────────────────────────────────────────────────────────────
result = components.html(html_page, height=10000, scrolling=False)

# ── Receber mensagens do iframe via component value ────────────────────────────
# O components.html não suporta retorno de valor diretamente.
# Usamos um st.text_input invisível como ponte de comunicação.
# O JS injeta o valor via postMessage → Streamlit recebe via query_params.

# Lê a pergunta do query param (quando o iframe redireciona via link)
qp = st.query_params
if "q" in qp:
    pergunta = qp.get("q", "").strip()
    farmacia = qp.get("db", "") or None
    action   = qp.get("a", "query")

    if action == "db":
        st.session_state.farmacia_filtro = farmacia if farmacia else None
        st.query_params.clear()
        st.rerun()
    elif action == "newchat":
        nid = str(uuid.uuid4())[:8]
        n = len(st.session_state.chats) + 1
        st.session_state.chats[nid] = {"nome": f"Nova Consulta #{n}", "historico": []}
        st.session_state.chat_ativo = nid
        st.query_params.clear()
        st.rerun()
    elif action == "selectchat":
        if pergunta in st.session_state.chats:
            st.session_state.chat_ativo = pergunta
        st.query_params.clear()
        st.rerun()
    elif pergunta:
        if farmacia is not None:
            st.session_state.farmacia_filtro = farmacia if farmacia else None
        st.session_state.pending_query = pergunta
        st.query_params.clear()
        st.rerun()


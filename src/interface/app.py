# ==============================================================================
# app.py — Farmazzini Intel 2.0  |  Native Streamlit (sem iframe)
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import sys, os, json, time, re, uuid
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime

import streamlit as st

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

st.set_page_config(
    page_title="Farmazzini Intel",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS: tema completo, sem nenhum chrome do Streamlit ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

:root {
  --red: #E63946; --red-deep: #8B0000; --red-mid: #B81D24;
  --bg: #080809; --surface: #0e0e10; --surface2: #131316;
  --border: rgba(255,255,255,0.07); --border-red: rgba(230,57,70,0.28);
  --text: #f0f0f2; --muted: #7a7a85;
  --font-d: 'Space Grotesk', sans-serif; --font-b: 'DM Sans', sans-serif;
}

/* Kill ALL Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }

html, body, .stApp {
  background: var(--bg) !important;
  font-family: var(--font-b) !important;
  color: var(--text) !important;
}

/* Remove all default Streamlit padding */
[data-testid="stAppViewContainer"] > section:first-child { padding: 0 !important; }
.main .block-container { padding: 0 2rem 1rem 2rem !important; max-width: 100% !important; }
[data-testid="stSidebar"] {
  background: rgba(10,10,13,0.95) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Chat bubbles */
.bubble-user {
  background: linear-gradient(140deg, #E63946 0%, #C01E27 45%, #7a0b12 100%);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 18px 18px 4px 18px;
  padding: 14px 18px; margin: 4px 0;
  color: #fff; font-size: 14px; line-height: 1.7;
  max-width: 72%; margin-left: auto;
  box-shadow: 0 8px 26px rgba(230,57,70,0.28);
  animation: msgIn 0.28s cubic-bezier(0.16,1,0.3,1);
}
.bubble-bot {
  background: rgba(18,18,24,0.7);
  border: 1px solid var(--border);
  border-radius: 18px 18px 18px 4px;
  padding: 14px 18px; margin: 4px 0;
  font-size: 14px; line-height: 1.7;
  max-width: 82%;
  animation: msgIn 0.28s cubic-bezier(0.16,1,0.3,1);
}
@keyframes msgIn {
  from { opacity:0; transform:translateY(10px); }
  to   { opacity:1; transform:translateY(0); }
}
.av-label-user {
  text-align: right; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 2px; color: rgba(255,255,255,0.5);
  margin-bottom: 3px; font-family: var(--font-d);
}
.av-label-bot {
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 2px; color: var(--red);
  margin-bottom: 3px; font-family: var(--font-d);
}

/* Metrics */
.metric-row { display: flex; gap: 12px; margin: 14px 0; flex-wrap: wrap; }
.metric-card {
  background: rgba(10,10,12,0.8);
  border: 1px solid var(--border); border-radius: 12px;
  padding: 12px 18px; flex: 1; min-width: 130px;
}
.metric-lbl {
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1.5px; color: var(--red); margin-bottom: 4px;
  font-family: var(--font-d);
}
.metric-val {
  font-size: 20px; font-weight: 700; color: #fff;
  font-family: var(--font-d);
}

/* SQL block */
.sql-block {
  background: rgba(8,8,10,0.9); border: 1px solid var(--border);
  border-left: 3px solid var(--red); border-radius: 10px;
  padding: 12px 14px; font-family: monospace; font-size: 12px;
  color: #aaa; white-space: pre-wrap; word-break: break-all;
  margin-top: 10px;
}

/* Attack block */
.atk-block {
  border-left: 3px solid var(--red); padding: 12px 16px;
  background: rgba(230,57,70,0.05); border-radius: 0 12px 12px 0;
  margin-top: 10px; font-size: 13px; line-height: 1.75;
}

/* Table */
.tbl-wrap { margin-top: 12px; overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
.tbl { width: 100%; border-collapse: collapse; background: rgba(8,8,10,0.65); font-size: 13px; }
.tbl th { text-align: left; color: var(--red); padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 10px; text-transform: uppercase; letter-spacing: 1px; white-space: nowrap; font-family: var(--font-d); }
.tbl td { padding: 11px 14px; border-bottom: 1px solid rgba(255,255,255,0.03); color: #e0e0e0; white-space: nowrap; }
.tbl tr:last-child td { border-bottom: none; }
.tbl tr:hover td { background: rgba(230,57,70,0.04); }

/* Hot buttons */
.hot-btn-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }

/* Streamlit buttons override */
[data-testid="stButton"] > button {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid var(--border) !important;
  color: #d0d0d0 !important; border-radius: 10px !important;
  font-family: var(--font-b) !important; font-weight: 600 !important;
  transition: all 0.16s !important;
}
[data-testid="stButton"] > button:hover {
  border-color: var(--red) !important;
  color: #fff !important; background: rgba(230,57,70,0.09) !important;
}
[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #E63946 0%, #B81D24 50%, #7a0b12 100%) !important;
  color: #fff !important; border-radius: 24px !important;
  box-shadow: 0 4px 16px rgba(230,57,70,0.28) !important;
}
[data-testid="stTextInput"] input {
  background: rgba(12,12,15,0.96) !important;
  border: 1px solid var(--border) !important;
  border-radius: 28px !important; color: var(--text) !important;
  font-family: var(--font-b) !important; font-size: 14px !important;
}
[data-testid="stTextInput"] input:focus { border-color: rgba(230,57,70,0.38) !important; }
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important; border-radius: 12px !important;
}

/* Sidebar section */
.sb-section { font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 2px; color: var(--red); margin: 12px 0 6px; font-family: var(--font-d); }

/* Header */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 0 14px; border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
.logo-txt { font-family: var(--font-d); font-size: 22px; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase; }
.logo-txt em { color: var(--red); font-style: normal; }
.badge-conn {
  background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.35);
  color: #10b981; padding: 4px 12px; border-radius: 6px;
  font-size: 10px; font-weight: 700; text-transform: uppercase;
}

hr.divider { border: none; border-top: 1px solid var(--border); margin: 8px 0; }
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


# ── AWS helpers ────────────────────────────────────────────────────────────────
def gerar_sql(prompt: str, farmacia_filtro: str = None) -> tuple:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    p = f"{prompt} (considere apenas farmacia='{farmacia_filtro}')" if farmacia_filtro else prompt
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
            stateMachineArn=STATE_MACHINE, input=json.dumps({"query": sql})
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


def gerar_contra_ataque(df: pd.DataFrame) -> str:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    resumo = df.to_string(index=False, max_rows=5)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": (
            f"Com base nestes dados de mercado farmacêutico:\n{resumo}\n\n"
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
        return f"Erro: {e}"


# ── Helpers de renderização ────────────────────────────────────────────────────
def build_metrics_html(df: pd.DataFrame) -> str:
    total = len(df)
    media_orig = "—"
    menor_pix  = "—"
    disp_count = "—"
    farm_count = "—"

    if "preco_original" in df.columns:
        s = pd.to_numeric(df["preco_original"], errors="coerce").dropna()
        if not s.empty: media_orig = f"R$ {s.mean():,.2f}"
    if "preco_pix" in df.columns:
        s = pd.to_numeric(df["preco_pix"], errors="coerce").dropna()
        if not s.empty: menor_pix = f"R$ {s.min():,.2f}"
    if "disponibilidade" in df.columns:
        disp_count = str(df["disponibilidade"].eq("Disponível").sum())
    if "farmacia" in df.columns:
        farm_count = str(df["farmacia"].nunique())

    return f"""<div class="metric-row">
  <div class="metric-card"><div class="metric-lbl">Registros</div><div class="metric-val">{total:,}</div></div>
  <div class="metric-card"><div class="metric-lbl">Preço Médio</div><div class="metric-val">{media_orig}</div></div>
  <div class="metric-card"><div class="metric-lbl">Menor PIX</div><div class="metric-val">{menor_pix}</div></div>
  <div class="metric-card"><div class="metric-lbl">{'Disponíveis' if 'disponibilidade' in df.columns else 'Farmácias'}</div>
    <div class="metric-val">{'disp_count' if 'disponibilidade' in df.columns else farm_count}</div></div>
</div>"""


def build_table_html(df: pd.DataFrame, max_rows: int = 50) -> str:
    df_show = df.head(max_rows).fillna("—")
    ths = "".join(f"<th>{c}</th>" for c in df_show.columns)
    trs = "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>"
        for row in df_show.values
    )
    note = f"<small style='color:#666;font-size:11px;'>Exibindo {min(max_rows, len(df))} de {len(df)} registros.</small>" if len(df) > max_rows else ""
    return f"""<div class="tbl-wrap"><table class="tbl">
  <thead><tr>{ths}</tr></thead>
  <tbody>{trs}</tbody>
</table></div>{note}"""


# ── Session state ──────────────────────────────────────────────────────────────
def _init():
    if "chats" not in st.session_state:
        pid = str(uuid.uuid4())[:8]
        st.session_state.chats = {
            pid: {
                "nome": "Análise Inicial",
                "historico": [],
                "criado_em": datetime.now().strftime("%H:%M"),
            }
        }
        st.session_state.chat_ativo = pid
    if "chat_ativo" not in st.session_state:
        st.session_state.chat_ativo = list(st.session_state.chats.keys())[0]
    if "farmacia_filtro" not in st.session_state:
        st.session_state.farmacia_filtro = None
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None

_init()


def chat_atual():
    return st.session_state.chats[st.session_state.chat_ativo]


def processar_pergunta(pergunta: str):
    chat = chat_atual()
    if not chat["historico"] and chat["nome"].startswith("Nova Consulta"):
        chat["nome"] = (pergunta[:22] + "…") if len(pergunta) > 22 else pergunta

    chat["historico"].append({"role": "user", "content": pergunta})

    farmacia = st.session_state.farmacia_filtro

    with st.spinner("🧠 Claude Haiku gerando SQL…"):
        sql, erro = gerar_sql(pergunta, farmacia)

    if erro:
        chat["historico"].append({"role": "bot", "type": "error", "content": f"Erro ao gerar SQL: {erro}"})
        return

    with st.spinner("🛡️ Executando no Athena via Step Functions…"):
        status, erro2, status_resp = executar_sql(sql)

    if erro2 or status != "SUCCEEDED":
        chat["historico"].append({"role": "bot", "type": "error", "content": erro2 or f"Status: {status}", "sql": sql})
        return

    with st.spinner("📦 Buscando resultado no S3…"):
        df, erro3 = buscar_s3(status_resp)

    if erro3:
        chat["historico"].append({"role": "bot", "type": "error", "content": f"Erro S3: {erro3}", "sql": sql})
        return

    if df is None or df.empty:
        chat["historico"].append({"role": "bot", "type": "empty", "sql": sql})
    else:
        chat["historico"].append({"role": "bot", "type": "result", "df": df, "sql": sql})


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 4px">
      <span style="font-family:'Space Grotesk',sans-serif;font-size:1.1rem;font-weight:700;
                   letter-spacing:2px;text-transform:uppercase;">
        Farma<span style="color:#E63946;">zzini</span>
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section">Base de Dados</div>', unsafe_allow_html=True)
    opcao = st.radio("Base", ["Todas", "FarmaPonte", "Vera Cruz"],
                     horizontal=True, label_visibility="collapsed")
    st.session_state.farmacia_filtro = None if opcao == "Todas" else opcao

    st.markdown("---")
    st.markdown('<div class="sb-section">Atalhos Rápidos</div>', unsafe_allow_html=True)

    atalhos = {
        "📦 Estoque Crítico":   "Quais produtos estão Indisponíveis hoje nas farmácias?",
        "🏷️ Mais Barato":       "Qual o produto mais barato disponível por farmácia?",
        "🔥 Maiores Promoções": "Liste os 10 produtos com maior desconto padrão disponíveis.",
        "💊 Preço Médio":       "Qual o preço médio dos produtos disponíveis por farmácia?",
        "💳 Comparar PIX":      "Compare os preços PIX médios entre FarmaPonte e Vera Cruz.",
    }
    for label, pergunta in atalhos.items():
        if st.button(label, key=f"hot_{label}", use_container_width=True):
            st.session_state.pending_query = pergunta

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#555;font-family:'DM Sans',sans-serif;line-height:2;">
      Modelo: Claude Haiku 4.5<br>
      Região: us-east-2<br>
      Data: 26/05/2026<br>
      Equipe: 06 — Poli Júnior
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="sb-section">Chats</div>', unsafe_allow_html=True)

    busca = st.text_input("Buscar", placeholder="🔍 Buscar chats…", label_visibility="collapsed")

    for cid, c in list(st.session_state.chats.items()):
        if busca.lower() not in c["nome"].lower():
            continue
        ativo = cid == st.session_state.chat_ativo
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(("▶ " if ativo else "") + c["nome"],
                         key=f"sel_{cid}", use_container_width=True,
                         type="primary" if ativo else "secondary"):
                st.session_state.chat_ativo = cid
                st.rerun()
        with col2:
            if len(st.session_state.chats) > 1:
                if st.button("🗑", key=f"del_{cid}"):
                    del st.session_state.chats[cid]
                    st.session_state.chat_ativo = list(st.session_state.chats.keys())[0]
                    st.rerun()

    if st.button("＋ Novo Chat", use_container_width=True):
        nid = str(uuid.uuid4())[:8]
        n = len(st.session_state.chats) + 1
        st.session_state.chats[nid] = {
            "nome": f"Nova Consulta #{n}",
            "historico": [],
            "criado_em": datetime.now().strftime("%H:%M"),
        }
        st.session_state.chat_ativo = nid
        st.rerun()


# ── Header ─────────────────────────────────────────────────────────────────────
col_logo, col_badge = st.columns([3, 1])
with col_logo:
    farmacia_label = st.session_state.farmacia_filtro or "Todas"
    st.markdown(f"""
    <div class="page-header">
      <div>
        <span class="logo-txt">Farmazzini <em>Intel</em></span>
        <span style="margin-left:12px;font-size:11px;color:#7a7a85;">
          Base: <strong style="color:#f0f0f2;">{farmacia_label}</strong>
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)
with col_badge:
    st.markdown("""
    <div style="text-align:right;padding-top:18px;">
      <span class="badge-conn">✨ Bedrock Ativo</span>
    </div>
    """, unsafe_allow_html=True)

# ── Processar query pendente (atalhos da sidebar) ──────────────────────────────
if st.session_state.pending_query:
    processar_pergunta(st.session_state.pending_query)
    st.session_state.pending_query = None

# ── Histórico de mensagens ─────────────────────────────────────────────────────
chat = chat_atual()

if not chat["historico"]:
    st.markdown("""
    <div class="bubble-bot">
      Olá! Seja bem-vindo ao <strong style="color:#E63946;">Farmazzini Intel 2.0</strong>.<br><br>
      Estou conectado ao <strong>Amazon Bedrock (Claude Haiku 4.5)</strong> e ao banco de dados real via Athena.<br><br>
      Posso analisar <strong>preços, estoque, promoções e cashback</strong> das farmácias FarmaPonte e Vera Cruz.<br><br>
      Use os atalhos rápidos na sidebar ou faça uma consulta abaixo!
    </div>
    """, unsafe_allow_html=True)

for idx, msg in enumerate(chat["historico"]):
    if msg["role"] == "user":
        st.markdown(f'<div class="av-label-user">Você</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)

    elif msg["role"] == "bot":
        st.markdown('<div class="av-label-bot">💊 Farmazzini Intel</div>', unsafe_allow_html=True)

        if msg["type"] == "error":
            err_html = f'<div class="bubble-bot">❌ <strong>Erro:</strong> {msg["content"]}</div>'
            if msg.get("sql"):
                err_html = err_html[:-6] + f'<div class="sql-block">{msg["sql"]}</div></div>'
            st.markdown(err_html, unsafe_allow_html=True)

        elif msg["type"] == "empty":
            empty_html = '<div class="bubble-bot">✅ Consulta executada — nenhum registro correspondeu aos filtros.'
            if msg.get("sql"):
                empty_html += f'<div class="sql-block">{msg["sql"]}</div>'
            empty_html += '</div>'
            st.markdown(empty_html, unsafe_allow_html=True)

        elif msg["type"] == "result":
            df = msg["df"]
            metrics_html = build_metrics_html(df)
            table_html   = build_table_html(df)

            st.markdown(f"""
            <div class="bubble-bot">
              ✅ <strong>{len(df):,} registro(s) encontrado(s).</strong>
              {metrics_html}
              {table_html}
            </div>
            """, unsafe_allow_html=True)

            if msg.get("sql"):
                with st.expander("🗂️ Ver SQL gerado", expanded=False):
                    st.code(msg["sql"], language="sql")

            # CSV download
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Exportar CSV", data=csv_bytes,
                file_name="farmazzini_resultado.csv", mime="text/csv",
                key=f"csv_{idx}",
            )

            # Contra-ataque
            if st.button("⚡ Sugerir Contra-Ataque", key=f"atk_{idx}"):
                st.session_state[f"show_atk_{idx}"] = True

            if st.session_state.get(f"show_atk_{idx}"):
                if not st.session_state.get(f"atk_txt_{idx}"):
                    with st.spinner("✨ Claude analisando estratégia…"):
                        txt = gerar_contra_ataque(df)
                    st.session_state[f"atk_txt_{idx}"] = txt

                txt = st.session_state[f"atk_txt_{idx}"]
                txt_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", txt).replace("\n", "<br>")
                st.markdown(f"""
                <div class="atk-block">
                  <strong style="color:#E63946;display:block;margin-bottom:8px;">
                    ⚡ Contra-Ataque Estratégico:
                  </strong>
                  {txt_fmt}
                </div>
                """, unsafe_allow_html=True)

st.markdown("---")

# ── Input ──────────────────────────────────────────────────────────────────────
col_inp, col_btn = st.columns([5, 1])
with col_inp:
    user_input = st.text_input(
        "Consulta", placeholder="Faça uma consulta estratégica ao mercado…",
        label_visibility="collapsed", key="main_input",
    )
with col_btn:
    enviar = st.button("Analisar →", type="primary", use_container_width=True)

if enviar and user_input.strip():
    processar_pergunta(user_input.strip())
    st.rerun()
elif enviar and not user_input.strip():
    st.warning("Digite uma consulta antes de enviar.")

# Limpar conversa
if chat["historico"]:
    if st.button("🗑️ Limpar conversa", key="limpar"):
        chat["historico"] = []
        st.rerun()
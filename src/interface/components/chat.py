# ==============================================================================
# components/chat.py — Componente Principal de Chat (Nativo & Sem Interrupções)
# Design fiel ao HTML sandbox: hot buttons, botões inline e AWS Bedrock
# Projeto Farmazzini | Poli Júnior | Equipe 06
# ==============================================================================

import streamlit as st
import pandas as pd
from utils.config import HOT_TRIGGERS, SYSTEM_PROMPT, DB_FILTER_PROMPTS, PRODUCTS_DB
from utils.aws_client import get_bedrock_client, query_claude_bedrock, is_bedrock_available

# ── MENSAGEM DE BOAS-VINDAS ──────────────────────────────────────────────────
WELCOME_MESSAGE = """
Olá, Pedro! Seja bem-vindo ao **Farmazzini Intel 2.0**.

O console de Inteligência Artificial está ativo e integrado ao **Claude via AWS Bedrock**.  
Posso te auxiliar em análises de:

- 📦 **Estoque físico** e alertas de ruptura  
- 🏷️ **Menor preço do mercado** em tempo real  
- 📊 **Preço médio regional** entre concorrentes  
- 🔥 **Regras de promoção complexas** da FarmaPonte e Vera Cruz  

Experimente os atalhos rápidos abaixo ou faça qualquer pergunta estratégica!
"""

# ── GRÁFICO INLINE ─────────────────────────────────────────────────────────
def _render_inline_chart(query_key: str):
    """
    Renderiza um gráfico de barras comparativo diretamente no chat.
    """
    chart_data = {
        "dipirona":  {"title": "Dipirona 500mg",        "labels": ["FarmaPonte\nR$14,90", "Vera Cruz\nR$8,94", "Farmazzini\nR$11,50"], "vals": [14.90, 8.94, 11.50]},
        "losartana": {"title": "Losartana 50mg",         "labels": ["FarmaPonte\nR$18,50", "Vera Cruz\nR$13,90", "Farmazzini\nR$15,90"], "vals": [18.50, 13.90, 15.90]},
        "neosaldina":{"title": "Neosaldina 30 drg",      "labels": ["FarmaPonte\nR$18,20", "Vera Cruz\nR$21,90", "Farmazzini\nR$22,50"], "vals": [18.20, 21.90, 22.50]},
        "pampers":   {"title": "Fralda Pampers G",       "labels": ["FarmaPonte\nR$64,90", "Vera Cruz\nR$49,90", "Farmazzini\nR$59,90"], "vals": [64.90, 49.90, 59.90]},
    }

    key = "dipirona"
    for k in chart_data:
        if k in query_key.lower():
            key = k
            break

    d = chart_data[key]
    df = pd.DataFrame({"Concorrente": d["labels"], "Preço (R$)": d["vals"]})
    df = df.set_index("Concorrente")

    st.markdown(
        f'<div style="font-size:13px; color:#E63946; font-weight:700; margin-top:14px; margin-bottom:8px; font-family:\'Space Grotesk\', sans-serif;">'
        f'📊 Comparativo de Preços: {d["title"]}</div>',
        unsafe_allow_html=True,
    )
    st.bar_chart(df, color="#E63946", height=180)

# ── CONTRA-ATAQUE ──────────────────────────────────────────────────────────
def _render_counter_attack(original_query: str, db_filter: str):
    """
    Gera sugestão de contra-ataque via IA ou resposta demo.
    """
    counter_prompt = (
        f"Com base na análise: '{original_query}', sugira 2-3 táticas de contra-ataque "
        f"estratégico para a Farmazzini. Seja direto, executivo e use **negrito** nos pontos-chave."
    )

    with st.spinner("⚡ Gerando tática de defesa..."):
        response = _get_ai_response(counter_prompt, db_filter)

    st.markdown(
        """
        <div style="background:rgba(230,57,70,0.06); border:1px solid rgba(230,57,70,0.25);
                    border-radius:12px; padding:14px 16px; margin-top:14px; font-family:\'DM Sans\', sans-serif;">
            <strong style="color:#E63946; font-size:14px; display:block; margin-bottom:6px;">
                ⚡ Contra-Ataque Estratégico Proposto:
            </strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(response)

# ── EXPORTAR CSV ────────────────────────────────────────────────────────────
def _export_csv():
    """Prepara CSV com todos os dados de preço para download."""
    rows = []
    for p in PRODUCTS_DB:
        rows.append({
            "Produto": p["name"],
            "EAN": p["ean"],
            "Estoque": p["estoque"],
            "Status": p["status"],
            "Farmazzini": p["farmazzini"],
            "FarmaPonte": p["farmaponte"],
            "Promo FarmaPonte": p["farmaponte_promo"],
            "Vera Cruz": p["veracruz"],
            "Vera Cruz PIX": p.get("veracruz_pix", ""),
            "Promo Vera Cruz": p["veracruz_promo"],
        })
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")

# ── AI RESPONSE ────────────────────────────────────────────────────────────
def _get_ai_response(prompt: str, db_filter: str) -> str:
    if not is_bedrock_available():
        return _demo_response(prompt, db_filter)
    client = get_bedrock_client()
    db_filter_prompt = DB_FILTER_PROMPTS.get(db_filter, "")
    return query_claude_bedrock(
        client=client,
        user_prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        db_filter_prompt=db_filter_prompt,
    )

def _demo_response(prompt: str, db_filter: str) -> str:
    p = prompt.lower()
    if "estoque" in p or "crítico" in p:
        return """**⚠️ Alerta de Estoque Crítico — Curva A**

| Produto | Estoque | Status |
|---|---|---|
| Dipirona 500mg | **2 unidades** | 🔴 Ruptura Iminente |
| Losartana 50mg | **4 unidades** | 🟡 Baixo |

**Ação Recomendada:**
1. **Dipirona:** Emitir pedido de compra urgente. Perda estimada de 3-5 vendas/dia.
2. **Losartana:** Agendar reposição para próximas 48h.

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*"""

    elif "barato" in p or "dipirona" in p or "preço" in p:
        return """**💰 Análise de Menor Preço: Dipirona 500mg**

| Concorrente | Preço | Condição |
|---|---|---|
| **Vera Cruz** | **R$ 8,94** | PIX à vista |
| Farmazzini | R$ 11,50 | Preço regular |
| Vera Cruz Regular | R$ 12,90 | — |
| FarmaPonte | R$ 14,90 | Regular |

**Diferença:** Vera Cruz PIX está **R$ 2,56 mais barato** que a Farmazzini (–22%).

**Contra-ataque sugerido:**
- Oferecer desconto PIX de 10% → preço final **R$ 10,35**.
- Criar combo "Dipirona + Paracetamol" com desconto progressivo.

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*"""

    elif "promo" in p or "combo" in p:
        return """**🔥 Maiores Promoções Ativas — Concorrentes**

**FarmaPonte:**
- Dipirona 500mg: Leve 3 por **R$ 12,90/cada**
- Neosaldina 30 drg: **Combo Leve 3 Pague 2** ← oferta agressiva!

**Vera Cruz:**
- Dipirona: **R$ 8,94 no PIX**
- Fralda Pampers G: A partir de 2 unidades, **R$ 49,90/cada** (–9%)

**⚡ Plano de Contra-Ataque:**
- Neosaldina: lançar "Compre 2, desconto de 15%".
- Dipirona: cashback interno de R$ 2,00 para clientes fidelidade no PIX.

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*"""

    return f"""**📊 Análise Estratégica — Farmazzini Intel**

Recebi sua consulta sobre: *"{prompt}"*

Com base na base **{db_filter}**, posso analisar preços, margens e promoções.

Sugestões de perguntas:
- *"Qual a margem da Dipirona vs Vera Cruz?"*
- *"Quais produtos estão com estoque crítico?"*
- *"Sugira ações para melhorar a margem da Neosaldina"*

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*"""

# ── RENDER CHAT ────────────────────────────────────────────────────────────
def render_chat(db_filter: str, chat_id: str):
    """
    Renderiza o chat completo com mensagens, hot buttons, input e botões de ação.
    """
    chat_data = st.session_state.chats.get(chat_id, {"title": "Chat", "messages": []})
    messages = chat_data.get("messages", [])

    # ── BOAS-VINDAS ───────────────────────────────────────────────────────
    if not messages:
        with st.chat_message("assistant", avatar="💊"):
            st.markdown(WELCOME_MESSAGE)

    # ── HISTÓRICO ─────────────────────────────────────────────────────────
    for i, msg in enumerate(messages):
        role = msg["role"]
        avatar = "👤" if role == "user" else "💊"

        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

            # Botões de ação apenas nas respostas do assistente
            if role == "assistant" and i > 0:
                _render_action_buttons(msg, i, chat_id, db_filter)

    # ── HOT BUTTONS ───────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    hot_cols = st.columns(len(HOT_TRIGGERS))
    for col, (label, prompt) in zip(hot_cols, HOT_TRIGGERS.items()):
        with col:
            if st.button(label, use_container_width=True, key=f"hot_{label}_{chat_id}"):
                _send_message(prompt, db_filter, chat_id)
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── INPUT ─────────────────────────────────────────────────────────────
    if user_input := st.chat_input(
        "Faça uma consulta estratégica ou peça análise de preços...",
        key=f"chat_input_{chat_id}",
    ):
        _send_message(user_input, db_filter, chat_id)
        st.rerun()

def _render_action_buttons(msg: dict, msg_index: int, chat_id: str, db_filter: str):
    """
    Renderiza os botões de ação estruturados inline abaixo das mensagens.
    """
    messages = st.session_state.chats[chat_id]["messages"]
    user_query = ""
    if msg_index > 0 and messages[msg_index - 1]["role"] == "user":
        user_query = messages[msg_index - 1]["content"]

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    col1, col2, col3, _ = st.columns([2, 2, 2, 4])

    with col1:
        if st.button("📊 Gráfico", key=f"graph_{chat_id}_{msg_index}", help="Gerar gráfico comparativo", use_container_width=True):
            st.session_state[f"show_graph_{chat_id}_{msg_index}"] = True

    with col2:
        if st.button("⚡ Contra-Ataque", key=f"attack_{chat_id}_{msg_index}", help="Gerar tática de defesa", use_container_width=True):
            st.session_state[f"show_attack_{chat_id}_{msg_index}"] = True

    with col3:
        csv_data = _export_csv()
        st.download_button(
            label="📥 CSV",
            data=csv_data,
            file_name="farmazzini_analise.csv",
            mime="text/csv",
            key=f"csv_{chat_id}_{msg_index}",
            use_container_width=True
        )

    # Renderiza o gráfico inline sob demanda se o estado for verdadeiro
    if st.session_state.get(f"show_graph_{chat_id}_{msg_index}", False):
        with st.container():
            _render_inline_chart(user_query)

    # Renderiza a tática de contra-ataque sob demanda se o estado for verdadeiro
    if st.session_state.get(f"show_attack_{chat_id}_{msg_index}", False):
        with st.container():
            _render_counter_attack(user_query, db_filter)
            # Desativa o gatilho de renderização síncrona pós-exibição para evitar loops infinitos
            st.session_state[f"show_attack_{chat_id}_{msg_index}"] = False

def _send_message(prompt: str, db_filter: str, chat_id: str):
    """Adiciona a mensagem ao histórico ativo, chama a IA do Bedrock e preserva os estados."""
    _append_message(chat_id, "user", prompt)

    # Renomeação dinâmica inteligente do título do chat na barra lateral
    chat = st.session_state.chats.get(chat_id, {})
    if chat.get("title", "").startswith("Análise de Preço:") or chat.get("title", "").startswith("Chat") or len(chat.get("messages", [])) <= 2:
        short = prompt[:25] + "..." if len(prompt) > 25 else prompt
        st.session_state.chats[chat_id]["title"] = short

    with st.spinner("🔍 Analisando o mercado..."):
        response = _get_ai_response(prompt, db_filter)

    _append_message(chat_id, "assistant", response)

def _append_message(chat_id: str, role: str, content: str):
    if chat_id not in st.session_state.chats:
        st.session_state.chats[chat_id] = {"title": "Chat", "messages": []}
    st.session_state.chats[chat_id]["messages"].append({"role": role, "content": content})
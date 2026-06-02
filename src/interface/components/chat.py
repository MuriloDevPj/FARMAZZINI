"""
Componente principal de chat: renderiza mensagens, hot buttons e input.
Integrado com AWS Bedrock (Claude) para respostas de IA.
"""

import streamlit as st
from utils.config import HOT_TRIGGERS, SYSTEM_PROMPT, DB_FILTER_PROMPTS
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


def _get_ai_response(prompt: str, db_filter: str) -> str:
    """
    Obtém resposta da IA (Claude via Bedrock) ou retorna demo se não configurado.
    """
    if not is_bedrock_available():
        # ── MODO DEMO (sem credenciais AWS) ──────────────────────────────────
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
    """
    Resposta de demonstração quando AWS Bedrock não está configurado.
    Útil para testar o layout sem credenciais.
    """
    prompt_lower = prompt.lower()

    if "estoque" in prompt_lower or "crítico" in prompt_lower:
        return """
**⚠️ Alerta de Estoque Crítico — Curva A**

| Produto | Estoque | Status |
|---|---|---|
| Dipirona 500mg | **2 unidades** | 🔴 Ruptura Iminente |
| Losartana 50mg | **4 unidades** | 🟡 Baixo |

**Ação Recomendada:**
1. **Dipirona:** Emitir pedido de compra de urgência. Perda estimada de 3-5 vendas/dia.
2. **Losartana:** Agendar reposição para próximos 48h.

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*
"""
    elif "barato" in prompt_lower or "dipirona" in prompt_lower or "preço" in prompt_lower:
        return """
**💰 Análise de Menor Preço: Dipirona 500mg**

| Concorrente | Preço | Condição |
|---|---|---|
| **Vera Cruz** | **R$ 8,94** | PIX à vista |
| Farmazzini | R$ 11,50 | Preço regular |
| Vera Cruz Regular | R$ 12,90 | — |
| FarmaPonte | R$ 14,90 | Regular |

**Diferença:** Vera Cruz PIX está **R$ 2,56 mais barato** que a Farmazzini (–22%).

**Contra-ataque sugerido:**
1. Oferecer desconto PIX de 10% → preço final **R$ 10,35** (ainda acima do Vera Cruz, mas competitivo).
2. Criar combo "Dipirona + Paracetamol" com desconto progressivo para reter volume.

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*
"""
    elif "promo" in prompt_lower or "combo" in prompt_lower:
        return """
**🔥 Maiores Promoções Ativas — Concorrentes**

**FarmaPonte:**
- Dipirona 500mg: Leve 3 por **R$ 12,90/cada** (vs R$ 14,90 unitário)
- Neosaldina 30 drg: **Combo Leve 3 Pague 2** ← oferta agressiva!

**Vera Cruz:**
- Dipirona: **R$ 8,94 no PIX** (preço mais agressivo do mercado)
- Fralda Pampers G: A partir de 2 unidades, **R$ 49,90/cada** (–9%)

**⚡ Plano de Contra-Ataque:**
1. Neosaldina: lançar "Compre 2 leve desconto de 15%" para rivalizar o Leve 3 Pague 2.
2. Dipirona: criar cashback interno de R$ 2,00 para clientes fidelidade pagando no PIX.

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*
"""
    else:
        return f"""
**📊 Análise Estratégica — Farmazzini Intel**

Recebi sua consulta sobre: *"{prompt}"*

Com base na base de dados ativa (**{db_filter}**), posso analisar preços, margens e promoções de todos os produtos monitorados.

Tente perguntas mais específicas como:
- *"Qual a margem da Dipirona vs Vera Cruz?"*
- *"Quais produtos estão abaixo do preço de custo do concorrente?"*
- *"Sugira ações para melhorar a margem da Neosaldina"*

> 💡 *Modo Demo ativo — configure credenciais AWS Bedrock para IA real.*
"""


def render_chat(db_filter: str, chat_id: str):
    """
    Renderiza o componente completo de chat para o chat_id ativo.
    
    Args:
        db_filter: filtro de base de dados ativo ('todas', 'ponte', 'veracruz')
        chat_id: ID do chat ativo no session_state
    """
    chat_data = st.session_state.chats.get(chat_id, {"title": "Chat", "messages": []})
    messages = chat_data.get("messages", [])

    # ── MENSAGEM DE BOAS-VINDAS (1º acesso) ──────────────────────────────────
    if not messages:
        with st.chat_message("assistant", avatar="💊"):
            st.markdown(WELCOME_MESSAGE)

    # ── HISTÓRICO DE MENSAGENS ────────────────────────────────────────────────
    for msg in messages:
        role = msg["role"]
        avatar = "👤" if role == "user" else "💊"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    # ── HOT BUTTONS ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    hot_cols = st.columns(len(HOT_TRIGGERS))
    for col, (label, prompt) in zip(hot_cols, HOT_TRIGGERS.items()):
        with col:
            if st.button(label, use_container_width=True, key=f"hot_{label}_{chat_id}"):
                _send_message(prompt, db_filter, chat_id, auto_title=True)
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── INPUT DO USUÁRIO ──────────────────────────────────────────────────────
    if user_input := st.chat_input(
        "Faça uma consulta estratégica ou peça análise de preços...",
        key=f"chat_input_{chat_id}",
    ):
        _send_message(user_input, db_filter, chat_id, auto_title=True)
        st.rerun()


def _send_message(prompt: str, db_filter: str, chat_id: str, auto_title: bool = False):
    """
    Adiciona mensagem do usuário, obtém resposta da IA e salva no estado.
    """
    # Adiciona mensagem do usuário
    _append_message(chat_id, "user", prompt)

    # Auto-renomeia o chat com base na primeira pergunta
    if auto_title:
        chat = st.session_state.chats.get(chat_id, {})
        title = chat.get("title", "")
        if title.startswith("Nova Consulta") or not chat.get("messages"):
            short = prompt[:28] + "..." if len(prompt) > 28 else prompt
            st.session_state.chats[chat_id]["title"] = short

    # Obtém resposta da IA com spinner
    with st.spinner("🔍 Analisando o mercado..."):
        response = _get_ai_response(prompt, db_filter)

    # Adiciona resposta do assistente
    _append_message(chat_id, "assistant", response)


def _append_message(chat_id: str, role: str, content: str):
    """
    Adiciona uma mensagem ao chat especificado no session_state.
    """
    if chat_id not in st.session_state.chats:
        st.session_state.chats[chat_id] = {"title": "Chat", "messages": []}

    st.session_state.chats[chat_id]["messages"].append(
        {"role": role, "content": content}
    )
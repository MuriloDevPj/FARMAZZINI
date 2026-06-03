# 💊 Farmazzini Intel — Streamlit

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Estrutura dos arquivos

```
farmazzini/
├── app.py          # Ponto de entrada — NÃO alterar a lógica de bridge
├── pipeline.py     # ← SEU TRABALHO FICA AQUI
├── ui.py           # Design HTML/CSS — só alterar o visual
└── requirements.txt
```

---

## Onde plugar seu pipeline (`pipeline.py`)

| Função            | O que fazer                                      |
|-------------------|--------------------------------------------------|
| `pre_processar()` | NLP, intent detection, extração de entidades     |
| `montar_query()`  | Gerar SQL, prompt de LLM, embedding vetorial     |
| `executar_query()`| Conectar ao BD (psycopg2, SQLAlchemy, API, FAISS)|
| `formatar_resposta()` | Converter resultado em HTML para o chat     |

## Fluxo de dados

```
Usuário digita → sendMessage() [JS]
    → sendToStreamlit('send', {msg, db}) [JS]
        → query_params [Streamlit bridge]
            → app.py captura e chama processar_mensagem()
                → pipeline.py executa as 4 etapas
                    → resposta HTML volta para session_state
                        → ui.py renderiza o chat atualizado
```

## Bases de dados disponíveis

O parâmetro `db_filter` chega na função `processar_mensagem()` como:
- `"todas"` — consulta FarmaPonte + Vera Cruz
- `"ponte"` — apenas FarmaPonte  
- `"veracruz"` — apenas Vera Cruz

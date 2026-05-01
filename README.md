# Projeto Farmazzini.

Este projeto faz parte da consultoria para a **Farmazzini**, focado na automação de coleta de dados, análise competitiva de preços e integração inteligente em nuvem.

##  Objetivo
Realizar o web scraping dos concorrentes (**FarmaPonte** e **Drogaria Vera Cruz**), tratar os dados garantindo a consistência via EAN/GTIN e disponibilizar essas informações para integração com a AWS e consumo via Chatbot.

---

## Cronograma de Desenvolvimento

Acompanhamento das etapas conforme definido no material de **Kick-off**:

### **Etapa 1: Imersão no Contexto** 
* **Duração:** 1 Dia
- [x] Alinhamentos iniciais e realização do Kick-off.
- [x] Obtenção de acessos a sites, bancos de dados e ambiente AWS.
- [x] Definição de pontos focais e documentação técnica inicial.

### **Etapa 2: Extração e Tratamento dos Dados** 
* **Duração:** 1 Semana
- [ ] **Vera Cruz:** Extração via web scraping (Responsável: Murilo).
- [ ] **FarmaPonte:** Extração via web scraping (Responsável: Vitor).
- [ ] Coleta de indicadores obrigatórios: EAN (ou GTIN); nome do medicamento; marca do medicamento;
Preço com e sem desconto; descontos; nome da farmácia concorrente.
- [ ] Verificação de consistência e tratamento das bases de dados.

### **Etapa 3: Integração e Automação** 
* **Duração:** 1 Semana
- [ ] Centralização das informações extraídas num Bucket S3.
- [ ] Configuração do Amazon Glue Data Catalog e schemas de tabelas.
- [ ] Automação dos scripts via AWS Lambda, EventBridge e EC2.
- [ ] Configuração de atualização automática (frequência definida no cronograma).

### **Etapa 4: Chatbot de Busca** 
* **Duração:** 1.5 Semanas
- [ ] Configuração do modelo de LLM no Amazon Bedrock para Queries SQL.
- [ ] Implementação da interface do chatbot em Streamlit.
- [ ] Configuração do Query Engine utilizando Amazon Athena.

### **Etapa 5: Validação Final e Governança** 
* **Duração:** 0.5 Semana
- [ ] Elaboração da documentação de arquitetura, fluxos e metadados.
- [ ] Validação final dos dados com o time da Farmazzini.
- [ ] Apresentação e entrega oficial do projeto.

---

##  Estrutura do Repositório

A organização do ambiente:

* `data/`: Armazenamento local de dados.
    * `raw/`: Dados brutos.
    * `processed/`: Dados limpos.
* `docs/`: Documentação (Canvas de Escopo, Proposta Comercial).
* `src/scrapers/`: Motores de extração.
    * `veracruz/`: Scripts para a Drogaria Vera Cruz.
    * `farmaponte/`: Scripts para a FarmaPonte.
* `tests/`: Testes unitários para validar a qualidade dos dados.

---


##  Definição da Coleta 

 mapeamento de seletores 

* **EAN / GTIN**: Código identificador único (13 dígitos).
* **Nome do Medicamento**: Título completo do produto.
* **Marca**: Laboratório ou fabricante.
* **Preço Sem Desconto**: Valor original.
* **Preço com PIX**: Valor com desconto máximo à vista.
* **Preço com Cartão**: Valor para pagamento.
* **Desconto (%)**: Percentual de economia identificado.
* **Farmácia**: Nome da farmácia.

---

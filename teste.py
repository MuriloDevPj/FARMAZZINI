import pandas as pd
from src.scrapers.clean import limpar_base

# 1. Criando dados fictícios "problemáticos"
data = {
    "ean": ["12345678", "12345678", "INVALIDO", ""],
    "nome": ["Remédio A", "Remédio A", "Produto B", "Produto C"],
    "preco_pix": ["10.00", "10.00", "5.00", "2.00"],
    "disponivel": ["Indisponível", "Disponível", "Disponível", "Disponível"]
}

df_teste = pd.DataFrame(data)

print("--- DADOS ORIGINAIS DO TESTE ---")
print(df_teste)

# 2. Executando sua lógica de limpeza
df_resultado = limpar_base(df_teste, "Farmacia Teste")

print("\n--- RESULTADO APÓS LIMPEZA ---")
print(df_resultado)

# Validação Automática
assert len(df_resultado[df_resultado["ean"] == "12345678"]) == 1, "❌ Erro: A deduplicação falhou!"
assert df_resultado.loc[0, "disponivel"] == "Disponível", "❌ Erro: Não priorizou o item disponível!"
print("\n✅ Todos os testes de lógica passaram!")
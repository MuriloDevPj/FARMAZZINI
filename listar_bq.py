from google.cloud import bigquery

client = bigquery.Client.from_service_account_json("/Users/vitortakashi/FARMAZZINI/credenciais.json")

tabelas = [
    "Historico_Vendas_Farma_Ponte",
    "Historico_Vendas_Sao_Joao",
    "Historico_Vendas_Sao_Paulo",
    "Historico_Vendas_Vera_Cruz",
]

for tabela in tabelas:
    print(f"Exportando {tabela}...")
    query = f"SELECT * FROM `supple-fold-473517-h1.Farmacias.{tabela}`"
    df = client.query(query).to_dataframe()
    df.to_csv(f"{tabela}.csv", index=False, encoding="utf-8-sig")
    print(f"  -> {len(df)} linhas salvas em {tabela}.csv")

print("Concluído!")
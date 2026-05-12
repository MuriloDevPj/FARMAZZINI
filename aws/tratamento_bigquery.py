import pandas as pd
import boto3
from datetime import datetime
 
TABELAS = [
    "Historico_Vendas_Farma_Ponte",
    "Historico_Vendas_Sao_Joao",
    "Historico_Vendas_Sao_Paulo",
    "Historico_Vendas_Vera_Cruz",
]
 
BUCKET = "farmazzini-equipe6"
PROCESSED_PATH = "/Users/vitortakashi/FARMAZZINI/data/processed"
 
 
def limpar_dados(df, nome_tabela):
    # int64_field_0 — inteiro, None se vazio
    if "int64_field_0" in df.columns:
        df["int64_field_0"] = pd.to_numeric(df["int64_field_0"], errors="coerce").astype("Int64")

    # venda_id — inteiro, None se vazio
    if "venda_id" in df.columns:
        df["venda_id"] = pd.to_numeric(df["venda_id"], errors="coerce").astype("Int64")

    # nome_produto — string, None se vazio
    if "nome_produto" in df.columns:
        df["nome_produto"] = df["nome_produto"].where(df["nome_produto"].notna(), None)

    # data_venda — converte "01-2024" para date, None se vazio
    if "data_venda" in df.columns:
        df["data_venda"] = pd.to_datetime(df["data_venda"], format="%m-%Y", errors="coerce")
        df["data_venda"] = df["data_venda"].dt.date

    # quantidade — double, None se vazio
    if "quantidade" in df.columns:
        df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce")

    return df
 
 
def main():
    s3 = boto3.client("s3")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
 
    for tabela in TABELAS:
        print(f"Processando {tabela}...")
 
        df = pd.read_csv(f"/Users/vitortakashi/FARMAZZINI/{tabela}.csv")
        df = limpar_dados(df, tabela)
 
        arquivo_local = f"{PROCESSED_PATH}/{tabela}_clean_{timestamp}.parquet"
        df.to_parquet(arquivo_local, index=False)
        print(f"  -> Salvo em {arquivo_local}")
 
        s3_key = f"processed/{tabela}/{tabela}_clean_{timestamp}.parquet"
        s3.upload_file(arquivo_local, BUCKET, s3_key)
        print(f"  -> Enviado para s3://{BUCKET}/{s3_key}")
 
    print("\nConcluído!")
 
 
if __name__ == "__main__":
    main()
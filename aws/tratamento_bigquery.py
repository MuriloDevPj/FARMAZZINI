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
    for coluna in df.columns:
        df[coluna] = df[coluna].astype(str).replace("nan", "")
        if coluna in ["data_venda", "quantidade"]:
            df[coluna] = df[coluna].replace("", f"{coluna}_nao_identificada")
        else:
            df[coluna] = df[coluna].replace("", f"{coluna}_nao_identificado")
 
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
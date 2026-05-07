import pandas as pd
import os
from datetime import datetime
 
CREDENCIAIS = "/Users/vitortakashi/FARMAZZINI/credenciais.json"
 
TABELAS = [
    "Historico_Vendas_Farma_Ponte",
    "Historico_Vendas_Sao_Joao",
    "Historico_Vendas_Sao_Paulo",
    "Historico_Vendas_Vera_Cruz",
]
 
def limpar_dados(df, nome_tabela):
    print(f"Limpando {nome_tabela}...\n")
 
    if "quantidade" in df.columns:
        df = df.dropna(subset=["quantidade"]).copy()
        df["quantidade"] = df["quantidade"].astype(float).astype(int)
 
    if "nome_produto" in df.columns:
        df["nome_produto"] = df["nome_produto"].str.strip().str.title()
 
    df = df.drop_duplicates()
 
    return df
 
 
def main():
    data_hoje = datetime.now().strftime("%d-%m-%Y")
    os.makedirs("dados_limpos", exist_ok=True)
 
    for tabela in TABELAS:
        arquivo = f"{tabela}.csv"
 
        if not os.path.exists(arquivo):
            continue
 
        df = pd.read_csv(arquivo)
        df_limpo = limpar_dados(df, tabela)
        output = f"dados_limpos/{tabela}_limpo_{data_hoje}.csv"
        df_limpo.to_csv(output, index=False, encoding="utf-8-sig")
 
 
 
if __name__ == "__main__":
    main()

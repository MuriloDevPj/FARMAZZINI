import pandas as pd
 
TABELAS = [
    "Historico_Vendas_Farma_Ponte",
    "Historico_Vendas_Sao_Joao",
    "Historico_Vendas_Sao_Paulo",
    "Historico_Vendas_Vera_Cruz",
]
 
def limpar_dados(df, nome_tabela): 
    # 4. Converte todas as colunas para string e preenche vazios
    for coluna in df.columns:
        df[coluna] = df[coluna].astype(str).replace("nan", "")
        if coluna in ["data_venda", "quantidade"]:
            df[coluna] = df[coluna].replace("", f"{coluna}_nao_identificada")
        else:
            df[coluna] = df[coluna].replace("", f"{coluna}_nao_identificado")
            
    return df
 
def main():
    for tabela in TABELAS:
        df = pd.read_csv(f"{tabela}.csv")
        df = limpar_dados(df, tabela)
        from datetime import datetime
        data_hoje = datetime.now().strftime("%d-%m-%Y")
        df.to_parquet(f"{tabela}_limpo_{data_hoje}.parquet", index=False)
 
    print("\nConcluído!")
 
if __name__ == "__main__":
    main()
 
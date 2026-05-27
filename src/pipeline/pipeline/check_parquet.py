import pandas as pd

# Substitua pelo nome do arquivo que apareceu no seu log
caminho_parquet = "data/processed/veracruz_clean_20260507_153031.parquet"

# Lendo o arquivo Parquet
df = pd.read_parquet(caminho_parquet)

# Visualizando as 10 primeiras linhas e informações das colunas
print("--- PREVIA DOS DADOS ---")
print(df.head(10))

print("\n--- INFORMAÇÕES DO SCHEMA ---")
print(df.info())

print("\n--- CONTAGEM POR DISPONIBILIDADE ---")
print(df['disponivel'].value_counts())
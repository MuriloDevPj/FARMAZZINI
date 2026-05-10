import pandas as pd
import re
import os
from pathlib import Path
from datetime import datetime
import boto3  # Biblioteca oficial da AWS

S3_BUCKET_NAME = "farmazzini-equipe6"  # Nome uniforme da sua equipe

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Schema Canônico solicitado
COLS = ["ean", "nome", "marca", "preco_sem_desconto", "preco_pix", 
        "preco_cartao", "desconto", "disponivel", "farmacia"]

def normalizar_ean(val):
    if pd.isna(val) or str(val).strip() in ("", "nan", "None", "NONE"):
        return "NONE"
    digits = re.sub(r"\D", "", str(val))
    return digits if 8 <= len(digits) <= 14 else "NONE"

def normalizar_campo(val):
    if pd.isna(val) or str(val).strip() in ("", "nan", "None", "NONE"):
        return "NONE"
    return str(val).strip()

def limpar_base(df, nome_farmacia):
    """Padroniza, preenche vazios com NONE e deduplica por farmácia."""
    for col in COLS:
        if col not in df.columns:
            df[col] = "NONE"
    
    df = df[COLS].copy()
    df["farmacia"] = nome_farmacia
    df["ean"] = df["ean"].apply(normalizar_ean)
    df["nome"] = df["nome"].apply(normalizar_campo)
    df["marca"] = df["marca"].apply(normalizar_campo)
    df["disponivel"] = df["disponivel"].apply(normalizar_campo)
    
    df = df.replace({"": "NONE", "nan": "NONE", None: "NONE"})

    df_com_ean = df[df["ean"] != "NONE"].copy()
    df_sem_ean = df[df["ean"] == "NONE"].copy()

    df_com_ean = df_com_ean.sort_values(
        by=["ean", "disponivel"], 
        ascending=[True, True]
    ).drop_duplicates(subset=["ean"], keep="first")

    return pd.concat([df_com_ean, df_sem_ean], ignore_index=True)

def executar_limpeza():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    farmacias = {
        "veracruz": "Vera Cruz",
        "farmaponte": "FarmaPonte"
    }

    print(f"--- INICIANDO TRATAMENTO E UPLOAD PARA BUCKET: {S3_BUCKET_NAME} ---")

    for prefixo, nome_real in farmacias.items():
        # Busca o arquivo CSV mais recente em data/raw
        arquivos = sorted(RAW_DIR.glob(f"{prefixo}_*.csv"), reverse=True)
        
        if not arquivos:
            print(f"Erro: Nenhum arquivo bruto de {nome_real} encontrado.")
            continue
            
        csv_atual = arquivos[0]
        print(f"✨ Processando {nome_real}: {csv_atual.name}")
        
        # Leitura e Limpeza
        df_bruto = pd.read_csv(csv_atual, dtype=str, encoding="utf-8-sig")
        df_limpo = limpar_base(df_bruto, nome_real)
        
        # Gerar nome do arquivo final
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_saida = f"{prefixo}_clean_{timestamp}.parquet"
        
        # 1. SALVAMENTO LOCAL (Backup)
        caminho_local = PROCESSED_DIR / nome_saida
        df_limpo.to_parquet(caminho_local, index=False, engine="pyarrow")
        print(f"Backup local salvo: {caminho_local.name}")

        # 2. UPLOAD PARA AWS S3 (Integração)
        # O prefixo organiza os dados em "pastas" dentro do bucket
        caminho_s3 = f"s3://{S3_BUCKET_NAME}/processed/{prefixo}/{nome_saida}"
        
        try:
            # O Pandas utiliza o s3fs internamente para enviar o arquivo
            df_limpo.to_parquet(caminho_s3, index=False, engine="pyarrow")
            print(f"Upload concluído: {caminho_s3}")
        except Exception as e:
            print(f"Erro no upload S3: {e}")

if __name__ == "__main__":
    executar_limpeza()
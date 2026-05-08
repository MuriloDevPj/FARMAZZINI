import pandas as pd
import boto3
import io
import re
from datetime import datetime

# Configurações globais
S3_CLIENT = boto3.client('s3')
DEST_BUCKET = "farmazzini-equipe6"
COLS = ["ean", "nome", "marca", "preco_sem_desconto", "preco_pix", 
        "preco_cartao", "desconto", "disponivel", "farmacia"]

def normalizar_ean(val):
    if pd.isna(val) or str(val).strip().upper() in ("", "NAN", "NONE"):
        return "NONE"
    digits = re.sub(r"\D", "", str(val))
    return digits if 8 <= len(digits) <= 14 else "NONE"

def normalizar_campo(val):
    if pd.isna(val) or str(val).strip().upper() in ("", "NAN", "NONE"):
        return "NONE"
    return str(val).strip()

def limpar_base(df, nome_farmacia):
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
    
    # Prioriza 'Disponível' na deduplicação
    df_com_ean = df_com_ean.sort_values(
        by=["ean", "disponivel"], 
        ascending=[True, True]
    ).drop_duplicates(subset=["ean"], keep="first")
    
    return pd.concat([df_com_ean, df_sem_ean], ignore_index=True)

def lambda_handler(event, context):
    try:
        # 1. Identifica o arquivo que disparou o evento
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        
        print(f"Arquivo recebido: {file_key} no bucket {source_bucket}")
        
        # Filtro de segurança: processar apenas arquivos na pasta 'raw/'
        if not file_key.startswith('raw/'):
            return {'statusCode': 200, 'body': 'Arquivo fora da pasta raw. Ignorado.'}

        # 2. Determina a farmácia pelo nome do arquivo (ex: veracruz_...)
        prefixo = "veracruz" if "veracruz" in file_key.lower() else "farmaponte"
        nome_real = "Vera Cruz" if prefixo == "veracruz" else "FarmaPonte"

        # 3. Lê o CSV do S3 para a memória
        response = S3_CLIENT.get_object(Bucket=source_bucket, Key=file_key)
        df_bruto = pd.read_csv(io.BytesIO(response['Body'].read()), dtype=str, encoding="utf-8-sig")

        # 4. Executa a limpeza (sua lógica validada)
        df_limpo = limpar_base(df_bruto, nome_real)

        # 5. Converte DataFrame para Parquet em memória (Buffer)
        parquet_buffer = io.BytesIO()
        df_limpo.to_parquet(parquet_buffer, index=False, engine="pyarrow")

        # 6. Upload para a pasta 'processed/'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_key = f"processed/{prefixo}/{prefixo}_clean_{timestamp}.parquet"
        
        S3_CLIENT.put_object(
            Bucket=DEST_BUCKET,
            Key=new_key,
            Body=parquet_buffer.getvalue()
        )
        
        print(f"Sucesso! Arquivo processado e salvo em: {new_key}")
        
        return {
            'statusCode': 200,
            'body': f'Processado: {new_key}'
        }

    except Exception as e:
        print(f"Erro: {str(e)}")
        raise e
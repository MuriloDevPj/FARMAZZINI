import pandas as pd
import boto3
import io
import re
import numpy as np  
from datetime import datetime
import awswrangler as wr  

# Inicialização dos clientes AWS
glue = boto3.client('glue')
ec2_client = boto3.client('ec2', region_name='us-east-2') 
S3_CLIENT = boto3.client('s3')

DEST_BUCKET = "farmazzini-equipe6-ohio"
ID_DA_EC2 = 'i-002f020c4088ed2ea' 

# 1. MAPEAMENTO DE NOMES: De como vem no CSV (Chave) para como deve ir para o Data Lake (Valor)
MAPEAMENTO_COLUNAS = {
    "ean": "ean",
    "nome": "nome",
    "marca": "marca",
    "preço original": "preco_original",
    "preço pix": "preco_pix",
    "preço cartão": "preco_cartao",
    "desconto padrão": "desconto_padrao",
    "desconto pix": "desconto_pix",
    "promoções especiais": "promocoes_especiais",
    "porcentagem de cashback": "porcentagem_de_cashback",
    "gtin": "gtin",
    "disponibilidade": "disponibilidade",
    "farmácia": "farmacia"
}

def normalizar_ean(val):
    if pd.isna(val) or str(val).strip().upper() in ("", "NAN", "NONE"):
        return None  
    digits = re.sub(r"\D", "", str(val))
    return digits if 8 <= len(digits) <= 14 else None  

def normalizar_campo(val):
    if pd.isna(val) or str(val).strip().upper() in ("", "NAN", "NONE"):
        return None  
    return str(val).strip()

def normalizar_preco(val):
    if pd.isna(val) or str(val).strip().upper() in ("", "NAN", "NONE"):
        return None
    try:
        txt = re.sub(r"[^\d,.]", "", str(val))
        if ',' in txt and '.' in txt:
            txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt:
            txt = txt.replace(',', '.')
        return float(txt)
    except:
        return None

def limpar_base(df, nome_farmacia):
    # Garante que as colunas originais existam antes de renomear
    for col in MAPEAMENTO_COLUNAS.keys():
        if col not in df.columns:
            df[col] = None  
            
    df = df[list(MAPEAMENTO_COLUNAS.keys())].copy()
    df["farmácia"] = nome_farmacia
    
    # Aplica as higienizações usando os nomes originais do CSV
    df["ean"] = df["ean"].apply(normalizar_ean)
    df["nome"] = df["nome"].apply(normalizar_campo)
    df["marca"] = df["marca"].apply(normalizar_campo)
    df["disponibilidade"] = df["disponibilidade"].apply(normalizar_campo)
    
    for col in ["desconto padrão", "desconto pix", "promoções especiais", "porcentagem de cashback", "gtin"]:
        df[col] = df[col].apply(normalizar_campo)
    
    for col in ["preço original", "preço pix", "preço cartão"]:
        df[col] = df[col].apply(normalizar_preco)
    
    # Substitui variações de texto nulo por None
    df = df.replace({"": None, "nan": None, "NAN": None, "NONE": None})
    
    # 2. RENOMEA AS COLUNAS para o padrão limpo do Athena (Sem acentos/espaços)
    df = df.rename(columns=MAPEAMENTO_COLUNAS)
    
    # 3. FORÇA A TIPAGEM EXPLICITA usando os novos nomes limpos
    tipo_schema = {
        "ean": "string",
        "nome": "string",
        "marca": "string",
        "preco_original": "float64",
        "preco_pix": "float64",
        "preco_cartao": "float64",
        "desconto_padrao": "string",
        "desconto_pix": "string",
        "promocoes_especiais": "string",
        "porcentagem_de_cashback": "string",
        "gtin": "string",
        "disponibilidade": "string",
        "farmacia": "string"
    }
    
    for coluna, tipo in tipo_schema.items():
        if tipo == "string":
            df[coluna] = df[coluna].astype(str).replace({"None": None, "<NA>": None, "nan": None, "NaN": None})
        else:
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')

    # Remove duplicatas mantendo produtos disponíveis
    df_com_ean = df[df["ean"].notna()].copy()
    df_sem_ean = df[df["ean"].isna()].copy()
    
    df_com_ean = df_com_ean.sort_values(by=["ean", "disponibilidade"], ascending=[True, True])
    df_com_ean = df_com_ean.drop_duplicates(subset=["ean"], keep="first")
    
    return pd.concat([df_com_ean, df_sem_ean], ignore_index=True)

def lambda_handler(event, context):
    try:
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        
        print(f"Arquivo detectado: {file_key}")
        
        if not file_key.startswith('raw/'):
            return {'statusCode': 200, 'body': 'Arquivo fora do escopo raw/.'}

        prefixo = "veracruz" if "veracruz" in file_key.lower() else "farmaponte"
        nome_real = "Vera Cruz" if prefixo == "veracruz" else "FarmaPonte"

        response = S3_CLIENT.get_object(Bucket=source_bucket, Key=file_key)
        df_bruto = pd.read_csv(io.BytesIO(response['Body'].read()), dtype=str, encoding="utf-8-sig")

        df_limpo = limpar_base(df_bruto, nome_real)

        # Adiciona metadados temporais (Colunas de partição também em minúsculo)
        agora = datetime.utcnow()
        df_limpo["data_coleta"] = agora
        df_limpo["ano"] = agora.strftime('%Y')
        df_limpo["mes"] = agora.strftime('%m')
        df_limpo["dia"] = agora.strftime('%d')

        # Gravação física no S3
        s3_path_destino = f"s3://{DEST_BUCKET}/processed/"
        print(f"Gravando partições em: {s3_path_destino}")
        
        wr.s3.to_parquet(
            df=df_limpo,
            path=s3_path_destino,
            dataset=True,
            mode="overwrite_partitions",
            partition_cols=['farmacia', 'ano', 'mes', 'dia'], # Usando 'farmacia' sem acento
            boto3_session=boto3.Session(region_name="us-east-2")
        )
        print("Arquivo Parquet gravado com sucesso.")

        if "farmaponte" in file_key.lower():
            print("Executando encerramento do fluxo diário...")
            glue.start_crawler(Name='crawler-farmazzini-ohio-equipe6')
            ec2_client.stop_instances(InstanceIds=[ID_DA_EC2])
            print(f"Crawler iniciado e sinal STOP enviado para {ID_DA_EC2}.")
        
        return {'statusCode': 200, 'body': 'Sucesso!'}

    except Exception as e:
        print(f"Erro: {str(e)}")
        raise e
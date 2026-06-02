"""
Cliente AWS Bedrock para integração com Claude via Amazon Bedrock.
Substitui a API do Gemini pelo Claude (Anthropic) via AWS.

Configuração necessária:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION (ex: us-east-1)

Ou via variáveis de ambiente / st.secrets no Streamlit Cloud.
"""

import os
import json
import boto3
import streamlit as st
from typing import Optional


def get_bedrock_client():
    """
    Cria e retorna um cliente boto3 para o Amazon Bedrock Runtime.
    Tenta ler credenciais do st.secrets primeiro, depois das variáveis de ambiente.
    """
    try:
        # Tenta via Streamlit Secrets (produção no Streamlit Cloud)
        aws_access_key = st.secrets.get("AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = (
            st.secrets.get("AWS_DEFAULT_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

        if aws_access_key and aws_secret_key:
            client = boto3.client(
                "bedrock-runtime",
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
            )
        else:
            # Usa credenciais padrão da máquina (IAM Role ou ~/.aws/credentials)
            client = boto3.client("bedrock-runtime", region_name=aws_region)

        return client

    except Exception as e:
        st.error(f"❌ Erro ao conectar ao AWS Bedrock: {e}")
        return None


def query_claude_bedrock(
    client,
    user_prompt: str,
    system_prompt: str,
    db_filter_prompt: str = "",
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
    max_tokens: int = 1024,
) -> str:
    """
    Envia uma mensagem ao Claude via Amazon Bedrock e retorna o texto da resposta.

    Args:
        client: boto3 bedrock-runtime client
        user_prompt: Mensagem do usuário
        system_prompt: Instrução de sistema com contexto da Farmazzini
        db_filter_prompt: Filtro de base de dados (Todas / Ponte / Vera Cruz)
        model_id: ID do modelo Claude no Bedrock
        max_tokens: Número máximo de tokens na resposta

    Returns:
        Texto da resposta do modelo
    """
    if not client:
        return "❌ **Erro:** Cliente AWS Bedrock não inicializado. Verifique as credenciais."

    full_user_message = f"{db_filter_prompt}\n\nPergunta do Pedro Mazini: {user_prompt}" if db_filter_prompt else user_prompt

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": full_user_message,
            }
        ],
    }

    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    except client.exceptions.ThrottlingException:
        return "⚠️ **Limite de requisições atingido.** Aguarde alguns segundos e tente novamente."
    except client.exceptions.ModelNotReadyException:
        return "⚠️ **Modelo não disponível no momento.** Tente novamente em instantes."
    except Exception as e:
        error_msg = str(e)
        if "AccessDeniedException" in error_msg:
            return "❌ **Acesso Negado:** Verifique se o modelo Claude está habilitado na sua conta AWS e região."
        return f"❌ **Erro de Conexão AWS Bedrock:** {error_msg}"


def _get_secret(key: str) -> str:
    """Lê um segredo do Streamlit Secrets com fallback seguro."""
    try:
        return st.secrets.get(key, "") or ""
    except Exception:
        return ""


def is_bedrock_available() -> bool:
    """
    Verifica se as credenciais AWS estão configuradas.
    """
    has_key = bool(os.getenv("AWS_ACCESS_KEY_ID") or _get_secret("AWS_ACCESS_KEY_ID"))
    has_secret = bool(os.getenv("AWS_SECRET_ACCESS_KEY") or _get_secret("AWS_SECRET_ACCESS_KEY"))
    return has_key and has_secret
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import os
from botocore.exceptions import NoCredentialsError

def enviar_para_s3(caminho_local_arquivo):
    s3 = boto3.client('s3')
    nome_bucket = "farmazzini-equipe6"
    nome_arquivo = os.path.basename(caminho_local_arquivo)
    try:
        s3.upload_file(caminho_local_arquivo, nome_bucket, f"raw/{nome_arquivo}")
        print(f"Upload concluído com sucesso: raw/{nome_arquivo}")
    except Exception as e:
        print(f"Erro no upload S3: {e}")

BASE_URL     = "https://www.farmaponte.com.br"
CATEGORY_URL = "https://www.farmaponte.com.br/saude/medicamentos/"

# Define o nome do arquivo com a data atual e salva na pasta atual
nome_csv = f"farmaponte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
OUT_FILE = Path(f"/tmp/{nome_csv}")
DELAY_MIN  = 0.0
DELAY_MAX  = 0.0
MAX_WORKERS = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.farmaponte.com.br/",
}

# Colunas alinhadas ao schema compartilhado (mesmo que Vera Cruz + url)
COLS = ["ean","nome","marca","preco_sem_desconto","preco_pix",
        "preco_cartao","desconto","disponivel","farmacia"]


def get_page(url, session):
    for attempt in range(1, 4):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException:
            time.sleep(5 * attempt)
    return None


def clean_price(text):
    if not text:
        return ""
    cleaned = re.sub(r"[^\d,]", "", str(text)).replace(",", ".")
    try:
        value = float(cleaned)
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return ""


def clean_price_float(text):
    if not text:
        return None
    cleaned = re.sub(r"[^\d,]", "", str(text)).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def calc_discount(preco_sem_desconto, preco_pix):
    price_from = clean_price_float(preco_sem_desconto)
    price_to   = clean_price_float(preco_pix)
    if price_from and price_to and price_from > 0 and price_to < price_from:
        pct = round((1 - price_to / price_from) * 100)
        return f"{pct}%"
    return "0%"


def get_product_urls(session):
    urls = []
    first_soup = get_page(CATEGORY_URL, session)
    max_pages  = 1

    if first_soup:
        paginator = first_soup.find("div", string=re.compile(r"Página\s+\d+\s+de\s+\d+"))
        if paginator:
            m = re.search(r"de\s+(\d+)", paginator.get_text())
            if m:
                max_pages = int(m.group(1))

    for page_num in range(1, max_pages + 1):
        page_url = CATEGORY_URL if page_num == 1 else f"{CATEGORY_URL}?p={page_num}"
        soup = get_page(page_url, session)
        if not soup:
            continue

        links = soup.find_all("a", href=re.compile(r"/p$"))
        if not links:
            break

        for a in links:
            href = a.get("href", "")
            full = href if href.startswith("http") else BASE_URL + href
            urls.append(full)

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    return list(dict.fromkeys(urls))


def extract_product_data(url):
    session = requests.Session()
    session.headers.update(HEADERS)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    soup = get_page(url, session)

    if not soup:
        return None

    data = {col: "" for col in COLS}
    data["farmacia"] = "FarmaPonte"
    data["url"]      = url

    # Nome
    nome_el = soup.select_one("h1.name") or soup.select_one("h1")
    if nome_el:
        data["nome"] = nome_el.get_text(strip=True)

    # Marca
    marca_el = soup.select_one("a.title_marca") or soup.select_one(".title_marca")
    if marca_el:
        data["marca"] = marca_el.get_text(strip=True)

    # EAN
    script_el = soup.find("script", type="application/ld+json")
    if script_el:
        try:
            jdata   = json.loads(script_el.string or "")
            ean_val = str(jdata.get("gtin13", ""))
            if ean_val.isdigit() and 8 <= len(ean_val) <= 14:
                data["ean"] = ean_val
        except Exception:
            pass

    # Preço sem desconto
    preco_de_el = soup.select_one("p.unit-price, .unit-price")
    if preco_de_el:
        data["preco_sem_desconto"] = clean_price(preco_de_el.get_text())

    # Preço cartão (total = parcelas × valor)
    parcelas_el      = soup.select_one("strong.get_min_installments")
    valor_parcela_el = soup.select_one("strong.get_card_price")
    if parcelas_el and valor_parcela_el:
        n_match = re.search(r"\d+", parcelas_el.get_text())
        n       = int(n_match.group()) if n_match else 1
        val     = clean_price_float(valor_parcela_el.get_text())
        if val:
            total = n * val
            data["preco_cartao"] = (
                f"R$ {total:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            )
    elif valor_parcela_el:
        data["preco_cartao"] = clean_price(valor_parcela_el.get_text())

    # Preço PIX
    preco_pix_el = soup.select_one("p.seal-pix.sale-price-pix, p.sale-price-pix")
    if preco_pix_el:
        data["preco_pix"] = clean_price(preco_pix_el.get_text())

    # Fallbacks
    if not data["preco_pix"]:
        data["preco_pix"] = data["preco_cartao"]
    if not data["preco_sem_desconto"]:
        data["preco_sem_desconto"] = data["preco_cartao"]

    # Desconto
    data["desconto"] = calc_discount(data["preco_sem_desconto"], data["preco_pix"])

    # Disponibilidade
    data["disponivel"] = "Disponível" if data["preco_pix"] else "Indisponível"

    return data

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    product_urls = get_product_urls(session)
    print(f"Total de produtos encontrados: {len(product_urls)}")

    all_data = []
    total    = len(product_urls)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(extract_product_data, url): url for url in product_urls}
        for i, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result:
                all_data.append(result)
            if i % 100 == 0:
                print(f"[{i}/{total}]")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_data).reindex(columns=COLS)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Salvo em: {OUT_FILE}")


def lambda_handler(event, context):
    main()
    return {"statusCode": 200, "body": "OK"}

if __name__ == "__main__":
    main()
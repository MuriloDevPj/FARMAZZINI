import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
 
BASE_URL = "https://www.farmaponte.com.br"
CATEGORY_URL = "https://www.farmaponte.com.br/saude/medicamentos/"
OUTPUT_FILE = "farmaponte_medicamentos.csv"
MAX_PAGES = 267
DELAY_MIN = 0.3
DELAY_MAX = 0.5
MAX_WORKERS = 10
 
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
 
 
def get_page(url, session):
    for attempt in range(1, 4):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            time.sleep(5 * attempt)
    return None
 
 
def clean_price(text):
    if not text:
        return None
    cleaned = re.sub(r"[^\d,]", "", str(text)).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None
 
 
def calc_discount(price_from, price_to):
    if price_from and price_to and price_from > 0:
        return round((1 - price_to / price_from) * 100, 2)
    return None
 
 
def get_product_urls(session):
    urls = []
    for page_num in range(1, MAX_PAGES + 1):
        page_url = CATEGORY_URL if page_num == 1 else f"{CATEGORY_URL}?p={page_num}"
        if page_num % 30 == 0:
            print(f"Coletando página {page_num}/{MAX_PAGES}...")
 
        soup = get_page(page_url, session)
        if not soup:
            continue
 
        product_links = soup.select("div.item-product a.item-image[href]")
        if not product_links:
            break
 
        for a in product_links:
            href = a.get("href", "")
            if href.startswith("http"):
                urls.append(href)
            elif href.startswith("/"):
                urls.append(BASE_URL + href)
 
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
 
    return list(dict.fromkeys(urls))
 
 
def extract_product_data(url):
    session = requests.Session()
    session.headers.update(HEADERS)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    
    soup = get_page(url, session)
 
    data = {
        "farmacia": "FarmaPonte",
        "url": url,
        "nome": None,
        "marca": None,
        "ean_gtin": None,
        "preco_de": None,
        "preco_por": None,
        "preco_cartao": None,
        "preco_pix": None,
        "desconto_pct": None,
        "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
 
    nome_el = soup.select_one("h1.name") or soup.select_one("h1")
    if nome_el:
        data["nome"] = nome_el.get_text(strip=True)
 
    marca_el = soup.select_one("a.title_marca") or soup.select_one(".title_marca")
    if marca_el:
        data["marca"] = marca_el.get_text(strip=True)
 
    script_el = soup.find("script", type="application/ld+json")
    if script_el:
        try:
            jdata = json.loads(script_el.string or "")
            data["ean_gtin"] = str(jdata.get("gtin13", "")) or None
        except Exception:
            pass
 
    preco_de_el = soup.select_one("p.unit-price") or soup.select_one(".unit-price")
    if preco_de_el:
        data["preco_de"] = clean_price(preco_de_el.get_text())
 
    preco_por_el = soup.select_one("p.sale-price.money:not(.seal-pix)")
    if preco_por_el:
        data["preco_por"] = clean_price(preco_por_el.get_text())
 
    parcelas_el = soup.select_one("strong.get_min_installments")
    valor_parcela_el = soup.select_one("strong.get_card_price")
    if parcelas_el and valor_parcela_el:
        parcelas_txt = re.search(r"\d+", parcelas_el.get_text())
        parcelas = int(parcelas_txt.group()) if parcelas_txt else 1
        valor_parcela = clean_price(valor_parcela_el.get_text())
        if valor_parcela:
            data["preco_cartao"] = round(parcelas * valor_parcela, 2)
 
    preco_pix_el = soup.select_one("p.seal-pix.sale-price-pix") or soup.select_one("p.sale-price-pix")
    if preco_pix_el:
        data["preco_pix"] = clean_price(preco_pix_el.get_text())
     
    data["desconto_pct"] = calc_discount(data["preco_de"], data["preco_por"])
 
    return data
 
 
def main(): 
    session = requests.Session()
    session.headers.update(HEADERS)
 
    product_urls = get_product_urls(session)
    print(f"Total de produtos encontrados: {len(product_urls)}")
 
    all_data = []
    total = len(product_urls)
 
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(extract_product_data, url): url for url in product_urls}
        for i, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            all_data.append(result)

            if i % 100 == 0:
                print(f"[{i}/{total}]")
                pd.DataFrame(all_data).to_csv(
                    f"farmaponte_parcial_{i}.csv", index=False, encoding="utf-8-sig"
                )
 
    df = pd.DataFrame(all_data)
    col_order = [
        "farmacia", "nome", "marca", "ean_gtin",
        "preco_de", "preco_por", "preco_cartao", "preco_pix", "desconto_pct",
        "url", "data_coleta",
    ]
    df = df.reindex(columns=[c for c in col_order if c in df.columns])
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
 
if __name__ == "__main__":
    main()
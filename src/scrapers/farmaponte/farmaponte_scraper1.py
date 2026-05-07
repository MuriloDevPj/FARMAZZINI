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
OUTPUT_FILE = f"farmaponte-{datetime.now().strftime('%d-%m-%Y')}.csv"
DELAY_MIN = 0.0
DELAY_MAX = 0.0
MAX_WORKERS = 20
#tempo aproximado 4 minutos
 
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
    """Retorna string no formato 'R$ X,XX', igual ao padrão Vera Cruz."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\d,]", "", str(text)).replace(",", ".")
    try:
        value = float(cleaned)
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return ""


def clean_price_float(text):
    """Converte texto de preço para float (uso interno para cálculo de desconto)."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,]", "", str(text)).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def calc_discount(preco_sem_desconto: str, preco_pix: str) -> str:
    """Retorna desconto como string com '%', ex: '15%'. Igual ao padrão Vera Cruz."""
    price_from = clean_price_float(preco_sem_desconto)
    price_to = clean_price_float(preco_pix)
    if price_from and price_to and price_from > 0 and price_to < price_from:
        pct = round((1 - price_to / price_from) * 100)
        return f"{pct}%"
    return ""

 
def get_product_urls(session):
    urls = []
    max_pages = None

    # Detecta o total de páginas na primeira página
    first_soup = get_page(CATEGORY_URL, session)
    if first_soup:
        paginator = first_soup.find("div", string=re.compile(r"Página\s+\d+\s+de\s+\d+"))
        if paginator:
            match = re.search(r"de\s+(\d+)", paginator.get_text())
            if match:
                max_pages = int(match.group(1))
                print(f"Total de páginas detectado: {max_pages}")

    for page_num in range(1, max_pages + 1):
        page_url = CATEGORY_URL if page_num == 1 else f"{CATEGORY_URL}?p={page_num}"
        if page_num % 30 == 0:
            print(f"Coletando página {page_num}/{max_pages}...")
 
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
 
    # Colunas alinhadas ao padrão Vera Cruz
    data = {
        "ean": None,
        "nome": None,
        "marca": None,
        "preco_sem_desconto": "",
        "preco_pix": "",
        "preco_cartao": "",
        "desconto": "",
        "disponivel": None,
        "farmacia": "FarmaPonte",
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
            ean_val = str(jdata.get("gtin13", ""))
            data["ean"] = ean_val if ean_val.isdigit() and 8 <= len(ean_val) <= 14 else None
        except Exception:
            pass
 
    preco_de_el = soup.select_one("p.unit-price") or soup.select_one(".unit-price")
    if preco_de_el:
        data["preco_sem_desconto"] = clean_price(preco_de_el.get_text())

    parcelas_el = soup.select_one("strong.get_min_installments")
    valor_parcela_el = soup.select_one("strong.get_card_price")
    if parcelas_el and valor_parcela_el:
        parcelas_txt = re.search(r"\d+", parcelas_el.get_text())
        parcelas = int(parcelas_txt.group()) if parcelas_txt else 1
        valor_parcela = clean_price_float(valor_parcela_el.get_text())
        if valor_parcela:
            total = parcelas * valor_parcela
            data["preco_cartao"] = (
                f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
    elif valor_parcela_el:
        data["preco_cartao"] = clean_price(valor_parcela_el.get_text())

    preco_pix_el = soup.select_one("p.seal-pix.sale-price-pix") or soup.select_one("p.sale-price-pix")
    if preco_pix_el:
        data["preco_pix"] = clean_price(preco_pix_el.get_text())

    # Se não há preço PIX separado, usa o preço cartão (igual Vera Cruz)
    if not data["preco_pix"]:
        data["preco_pix"] = data["preco_cartao"]

    # Se não há preço sem desconto, usa o preço cartão (igual Vera Cruz)
    if not data["preco_sem_desconto"]:
        data["preco_sem_desconto"] = data["preco_cartao"]

    data["desconto"] = calc_discount(data["preco_sem_desconto"], data["preco_pix"])

    data["disponivel"] = "Disponível" if data["preco_sem_desconto"] else "Indisponível"
 
    return data
 
 
# Colunas na mesma ordem que Vera Cruz
COLS = ["ean", "nome", "marca", "preco_sem_desconto",
        "preco_pix", "preco_cartao", "desconto", "disponivel", "farmacia"]


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
    df = df.reindex(columns=COLS)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
 
if __name__ == "__main__":
    main()
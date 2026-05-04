"""
Scraper - FarmaPonte Medicamentos
===================================
Extrai dados de medicamentos de:
  https://www.farmaponte.com.br/saude/medicamentos/
 
Campos extraídos:
  - Nome do medicamento
  - Marca / Fabricante
  - EAN / GTIN (quando disponível na página do produto)
  - Preço sem desconto (p.unit-price)
  - Preço com desconto (p.sale-price)
  - Desconto (%)
  - Preço com cartão
 
Saída: farmaponte_medicamentos.csv
 
Dependências:
  pip3 install requests beautifulsoup4 lxml pandas
"""
 
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import logging
import re
import json
from datetime import datetime
 
# ─── Configurações ────────────────────────────────────────────────────────────
 
BASE_URL = "https://www.farmaponte.com.br"
CATEGORY_URL = "https://www.farmaponte.com.br/saude/medicamentos/"
OUTPUT_FILE = "farmaponte_medicamentos.csv"
 
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.farmaponte.com.br/",
} #simula um navegador
 
DELAY_MIN = 1.5 #define o delay
DELAY_MAX = 3.5
 
# ─── Logging ──────────────────────────────────────────────────────────────────
 
logging.basicConfig( #mostra o progresso
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("farmaponte_scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)
 
 
# ─── Helpers ──────────────────────────────────────────────────────────────────
 
def get_page(url, session): #acessa a pagina até desistir
    for attempt in range(1, 4):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            log.warning(f"Tentativa {attempt}/3 falhou para {url}: {e}")
            time.sleep(5 * attempt)
    log.error(f"Falha definitiva ao acessar: {url}")
    return None
 
 
def clean_price(text): #muda a virgula por ponto nos precos
    if not text:
        return None
    cleaned = re.sub(r"[^\d,]", "", str(text)).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None
 
 
def calc_discount(price_from, price_to): #calcula o desconto
    if price_from and price_to and price_from > 0:
        return round((1 - price_to / price_from) * 100, 2)
    return None
 
 
# ─── Paginação ────────────────────────────────────────────────────────────────
 
def get_product_urls(session):
    urls = []
    page_num = 1
 
    while True: #carrega a pagina um até a 267
        page_url = CATEGORY_URL if page_num == 1 else f"{CATEGORY_URL}?p={page_num}"
        log.info(f"Coletando lista de produtos — página {page_num}: {page_url}")
 
        soup = get_page(page_url, session)
        if not soup:
            break
 
        product_links = soup.select("div.item-product a.item-image[href]") #busca todos os links da pagina
 
        if not product_links:
            product_links = [
                a for a in soup.select("div.item-product a[href]")
                if a.get("href", "").endswith("/p") or "/p?" in a.get("href", "")
            ]
 
        if not product_links:
            log.info(f"Nenhum produto encontrado na página {page_num}. Encerrando paginação.")
            break
 
        page_urls = []
        for a in product_links:#verifica se precisa add o https antes e etc
            href = a.get("href", "")
            if href.startswith("http"):
                page_urls.append(href)
            elif href.startswith("/"):
                page_urls.append(BASE_URL + href)
 
        page_urls = list(dict.fromkeys(page_urls))
        urls.extend(page_urls)
        log.info(f"  -> {len(page_urls)} produtos encontrados (total: {len(urls)})")

        next_btn = (
            soup.select_one("a.next-page")
            or soup.select_one("a[aria-label='Proxima pagina']")
            or soup.select_one(".pagination a[rel='next']")
            or soup.select_one("a.pagination__next")
            or soup.select_one("li.next a")
        )

        if not next_btn:
            log.info("Ultima pagina atingida.")
            break
        """
        MAX_PAGES = 267
        if page_num >= MAX_PAGES:
            log.info("Ultima pagina atingida.")
            break
        """# para ler todas as paginas tira esse comentario e coloca na do next_btn sla oq
 
        page_num += 1
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))#seta o delay
 
    log.info(f"Total de URLs coletadas: {len(urls)}")
    return urls
 
 
# ─── Extração de dados do produto ─────────────────────────────────────────────
 
def extract_product_data(url, session):
    soup = get_page(url, session)
    if not soup:
        return {"url": url, "erro": "Falha ao carregar pagina"}
 
    data = {
        "farmacia": "FarmaPonte",
        "url": url,
        "nome": None,
        "marca": None,
        "ean_gtin": None,
        "preco_de": None,
        "preco_por": None,
        "desconto_pct": None,
        "preco_pix": None,
        "preco_cartao": None,
        "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
 
    # Nome
    nome_el = (
        soup.select_one("h1.name")#pega o primeiro elemento do h1.name
        or soup.select_one("h1.title")
        or soup.select_one("h1")
    )
    if nome_el:
        data["nome"] = nome_el.get_text(strip=True)#extrai o texto do nome
 
    # Marca — confirmado: <p class="brand">Eurofarma</p>
    marca_el = (
        soup.select_one("a.title_marca")
        or soup.select_one(".title_marca")
    )
    if marca_el:
        data["marca"] = marca_el.get_text(strip=True)
 
    # EAN / GTIN — extraído do JSON-LD (script type="application/ld+json")
    script_el = soup.find("script", type="application/ld+json")
    if script_el:
        try:
            jdata = json.loads(script_el.string or "")
            data["ean_gtin"] = str(jdata.get("gtin13", "")) or None
        except Exception:
            pass
 
    # Preço "de" — confirmado: <p class="unit-price"> R$ 396,19 </p>
    preco_de_el = soup.select_one("p.unit-price") or soup.select_one(".unit-price")
    if preco_de_el:
        data["preco_de"] = clean_price(preco_de_el.get_text())
 
    # Preco com desconto final — <p class="sale-price money"> (sem a classe seal-pix)
    preco_desconto_el = soup.select_one("p.sale-price.money:not(.seal-pix)")
    if preco_desconto_el:
        data["preco_por"] = clean_price(preco_desconto_el.get_text())

    # Desconto 
    data["desconto_pct"] = calc_discount(data["preco_de"], data["preco_por"])

    # Preco com pix — <p class="seal-pix sale-price sale-price-pix mb-0 money">
    preco_pix_el = soup.select_one("p.seal-pix.sale-price-pix") or soup.select_one("p.sale-price-pix")
    if preco_pix_el:
        data["preco_pix"] = clean_price(preco_pix_el.get_text())
 

    # Preco com cartao — multiplica parcelas × valor da parcela
    parcelas_el = soup.select_one("strong.get_min_installments")
    valor_parcela_el = soup.select_one("strong.get_card_price")
    if parcelas_el and valor_parcela_el:
        parcelas_txt = re.search(r"\d+", parcelas_el.get_text())#transforma o texto em numero
        parcelas = int(parcelas_txt.group()) if parcelas_txt else 1#transforma o numero em inteiro, se nn tiver é 1
        valor_parcela = clean_price(valor_parcela_el.get_text())#pega o valor da parcela
        if valor_parcela:
            data["preco_cartao"] = round(parcelas * valor_parcela, 2)
 
    return data
 
 
# ─── Main ─────────────────────────────────────────────────────────────────────
 
def main():
    log.info("=" * 60)# coiso q aparece para ver o progresso
    log.info("Iniciando scraper — FarmaPonte Medicamentos")
    log.info(f"URL base: {CATEGORY_URL}")
    log.info("=" * 60)
 
    session = requests.Session()
    session.headers.update(HEADERS)
 
    product_urls = get_product_urls(session)
 
    if not product_urls:
        log.error("Nenhum produto encontrado. Verifique os seletores CSS.")
        return
 
    all_data = []
    total = len(product_urls)
 
    for i, url in enumerate(product_urls, start=1): #para cada url, ele extrai os dados
        log.info(f"[{i}/{total}] Extraindo: {url}")
        product_data = extract_product_data(url, session)
        all_data.append(product_data)
 
        if i % 50 == 0:# salva a cada 50 coisos analisados
            pd.DataFrame(all_data).to_csv(
                f"farmaponte_parcial_{i}.csv", index=False, encoding="utf-8-sig"
            )
            log.info(f"  -> Salvo parcialmente: {i} produtos")
 
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
 
    df = pd.DataFrame(all_data) #forma q é salvo os produtos
    col_order = [
        "farmacia", "nome", "marca", "ean_gtin",
        "preco_de", "preco_por", "desconto_pct", "preco_cartao", "preco_pix", 
        "url", "data_coleta",
    ]
    df = df.reindex(columns=[c for c in col_order if c in df.columns])
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
 
    log.info("=" * 60)
    log.info(f"Extracao concluida! {len(df)} produtos salvos em '{OUTPUT_FILE}'")
    log.info("=" * 60)
 
    print("\n── Resumo ──────────────────────────────────────")
    print(f"  Total de produtos : {len(df)}")
    print(f"  Com nome    : {df['nome'].notna().sum()}")
    print(f"  Com marca    : {df['marca'].notna().sum()}")
    print(f"  Com preco 'de'    : {df['preco_de'].notna().sum()}")
    print(f"  Com preco 'por'   : {df['preco_por'].notna().sum()}")
    print(f"  Com preco cartao  : {df['preco_cartao'].notna().sum()}")
    print(f"  Com preco pix  : {df['preco_pix'].notna().sum()}")
    print(f"  Com EAN/GTIN      : {df['ean_gtin'].notna().sum()}")
    print(f"  Arquivo gerado    : {OUTPUT_FILE}")
    print("─────────────────────────────────────────────────\n")
 
 
if __name__ == "__main__":
    main()
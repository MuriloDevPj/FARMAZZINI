import asyncio
import csv
import json
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BUCKET_NAME = "farmazzini-equipe6"

def enviar_para_s3(caminho_local: Path) -> bool:
    """Envia o CSV gerado para s3://farmazzini-equipe6/raw/"""
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError
        s3         = boto3.client("s3")
        destino_s3 = f"raw/{caminho_local.name}"
        s3.upload_file(str(caminho_local), BUCKET_NAME, destino_s3)
        return True
    except Exception:
        return False

BASE     = "https://www.drogariaveracruz.com.br"
CATS     = [f"{BASE}/medicamentos/", f"{BASE}/generico/"]
SEM_DL   = 80
RETRIES  = 3
TIMEOUT  = httpx.Timeout(12.0, connect=6.0)
WORKERS  = max(2, multiprocessing.cpu_count() - 1)
# Na EC2 salva no diretório atual; localmente respeita a estrutura do projeto
_NOME_ARQUIVO = f"veracruz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
try:
    OUT_FILE = Path(__file__).resolve().parents[3] / "data" / "raw" / _NOME_ARQUIVO
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
except (IndexError, OSError):
    OUT_FILE = Path.cwd() / _NOME_ARQUIVO
COLS = ["ean", "nome", "marca", "preco_sem_desconto",
        "preco_pix", "preco_cartao", "desconto", "disponivel", "farmacia"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

_RE_JSONLD       = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
_RE_EAN_SCRIPT   = re.compile(r'"(?:gtin1[34]|gtin8|ean|eanCode|barcode)"\s*:\s*"(\d{8,14})"', re.I)
_RE_INDISPONIVEL = re.compile(r'Avise[\s-]*me', re.I)
_RE_LINK_HREF    = re.compile(r'href=["\']([^"\']+/p)["\']', re.I)
_RE_LINK_JSON    = re.compile(r'"link"\s*:\s*"(/[^"]+/p)"', re.I)


def _txt(tag) -> str:
    return tag.get_text(strip=True) if tag else ""

def _oculto(tag) -> bool:
    return "display:none" in (tag.get("style", "").replace(" ", "")) if tag else True

def _limpa_preco(texto: str) -> str:
    """'R$ 10,97 no cartão' → 'R$ 10,97'"""
    m = re.search(r'R\$\s*[\d.,]+', texto)
    return m.group(0) if m else ""

def _float(texto: str) -> float:
    try:
        return float(re.sub(r'[^\d,]', '', texto).replace(',', '.'))
    except (ValueError, AttributeError):
        return 0.0

def parse_html(html: str) -> dict | None:
    if not html or len(html) < 500:
        return None

    soup = BeautifulSoup(html, "lxml")

    ean = ""
    for bloco in _RE_JSONLD.findall(html):
        try:
            data  = json.loads(bloco)
            items = data if isinstance(data, list) else [data]
            for item in items:
                for key in ("gtin13", "gtin14", "gtin12", "gtin8", "ean"):
                    val = str(item.get(key, ""))
                    if val.isdigit() and 8 <= len(val) <= 14:
                        ean = val
                        break
                if ean:
                    break
        except (json.JSONDecodeError, AttributeError):
            continue
        if ean:
            break
    if not ean:
        m = _RE_EAN_SCRIPT.search(html)
        if m:
            ean = m.group(1)

    content = soup.select_one("#content-product")
    if not content:
        return None

    nome  = _txt(content.select_one("h1"))
    marca = _txt(content.select_one("h1 + div a, h1 ~ div a"))

    seal = content.select_one(".seal-pix strong, .sale-price-pix strong")
    preco_pix = _limpa_preco(_txt(seal)) if seal else ""

    prices_div   = content.select_one(".prices")
    cartao_tag   = prices_div.select_one(".sale-price strong") if prices_div else None
    preco_cartao = _limpa_preco(_txt(cartao_tag)) if cartao_tag else ""

    if not preco_pix:
        preco_pix = preco_cartao

    unit_tag = prices_div.select_one(".unit-price") if prices_div else None
    if unit_tag and not _oculto(unit_tag):
        preco_sem_desc = _limpa_preco(_txt(unit_tag))
    else:
        preco_sem_desc = preco_cartao   # sem desconto → igual ao cartão

    desc_tag = prices_div.select_one(".descont") if prices_div else None
    if desc_tag and not _oculto(desc_tag):
        desconto = _txt(desc_tag)
        if desconto == "0%":
            desconto = ""
    else:
        desconto = ""

    # Se há parcelas, preco_cartao = n × valor_parcela
    inst_div = content.select_one(".card-installments")
    n_tag    = inst_div.select_one(".get_min_installments") if inst_div else None
    val_tag  = inst_div.select_one(".get_card_price")       if inst_div else None

    if n_tag and val_tag:
        n     = int(re.sub(r'\D', '', _txt(n_tag)) or 1)
        val   = _float(_txt(val_tag))
        total = n * val
        preco_cartao = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    elif val_tag and not n_tag:
        preco_cartao = _limpa_preco(_txt(val_tag))

    disponivel = "Indisponível" if _RE_INDISPONIVEL.search(html) else "Disponível"

    return dict(
        ean=ean, nome=nome, marca=marca,
        preco_sem_desconto=preco_sem_desc,
        preco_pix=preco_pix, preco_cartao=preco_cartao,
        desconto=desconto, disponivel=disponivel,
        farmacia="Vera Cruz",
    )

async def fetch(client: httpx.AsyncClient, url: str) -> str:
    for attempt in range(RETRIES):
        try:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
            return r.text
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException):
            if attempt < RETRIES - 1:
                await asyncio.sleep(1.5 ** attempt)
    return ""

async def coletar_links(client: httpx.AsyncClient, sem: asyncio.Semaphore) -> set:
    def _extrair(html: str) -> set:
        links = set()
        for href in _RE_LINK_HREF.findall(html):
            links.add(href if href.startswith("http") else BASE + href)
        for path in _RE_LINK_JSON.findall(html):
            links.add(BASE + path)
        return links

    async def _paginar(base_url: str) -> set:
        links, page = set(), 1
        while True:
            async with sem:
                html = await fetch(client, f"{base_url}?p={page}")
            novos = _extrair(html)
            if not novos:
                break
            links |= novos
            page  += 1
        return links

    return set().union(*await asyncio.gather(*[_paginar(c) for c in CATS]))

async def producer(client, sem, links, queue):
    async def _dl(url):
        async with sem:
            await queue.put(await fetch(client, url))
    await asyncio.gather(*[_dl(u) for u in links])
    await queue.put(None)

async def consumer(queue, executor):
    loop, rows = asyncio.get_running_loop(), []
    while True:
        html = await queue.get()
        if html is None:
            break
        r = await loop.run_in_executor(executor, parse_html, html)
        if r:
            rows.append(r)
    return rows

async def main():
    sem    = asyncio.Semaphore(SEM_DL)
    limits = httpx.Limits(max_connections=SEM_DL + 20,
                          max_keepalive_connections=SEM_DL,
                          keepalive_expiry=30)

    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, limits=limits) as client:
        links = await coletar_links(client, sem)
        queue = asyncio.Queue(maxsize=500)
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            prod = asyncio.create_task(producer(client, sem, links, queue))
            rows = await consumer(queue, executor)
            await prod

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    asyncio.run(main())
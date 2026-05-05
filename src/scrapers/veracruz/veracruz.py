import asyncio
import csv
import json
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import httpx

BASE     = "https://www.drogariaveracruz.com.br"
CATS     = [f"{BASE}/medicamentos/", f"{BASE}/generico/"]
SEM_DL   = 80
RETRIES  = 3
TIMEOUT  = httpx.Timeout(12.0, connect=6.0)
WORKERS  = max(2, multiprocessing.cpu_count() - 1)
OUT_FILE = (
    Path(__file__).resolve().parents[3]
    / "data" / "raw"
    / f"veracruz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)
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

_RE_EAN      = re.compile(r'"(?:gtin1[34]|ean|eanCode|gtin|barcode)"\s*:\s*"(\d{8,14})"', re.I)
_RE_JSONLD   = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
_RE_H1       = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S | re.I)
_RE_TAG      = re.compile(r'<[^>]+>')
_RE_BRAND    = re.compile(r'"brand"\s*:\s*"([^"]+)"', re.I)
_RE_STRONG   = re.compile(r'<strong[^>]*>(R\$\s*[\d.,]+)</strong>', re.I)
_RE_PRECO    = re.compile(r'R\$\s*\d+[.,]\d+')
_RE_DESCONTO = re.compile(r'-(\d+)%')
_RE_LINK_HREF = re.compile(r'href=["\']([^"\']+/p)["\']', re.I)
_RE_LINK_JSON = re.compile(r'"link"\s*:\s*"(/[^"]+/p)"', re.I)

_RE_INDISPONIVEL = re.compile(r'Avise.me', re.I)

def parse_html(html: str) -> dict | None:
    if not html or len(html) < 500:
        return None

    # EAN
    ean = ""
    for bloco in _RE_JSONLD.findall(html):
        try:
            data  = json.loads(bloco)
            items = data if isinstance(data, list) else [data]
            for item in items:
                for key in ("gtin13", "gtin14", "gtin12", "gtin8", "ean"):
                    val = str(item.get(key, ""))
                    if val.isdigit() and 8 <= len(val) <= 14:
                        ean = val; break
                if ean: break
        except (json.JSONDecodeError, AttributeError):
            continue
        if ean: break
    if not ean:
        m = _RE_EAN.search(html)
        if m: ean = m.group(1)

    # Nome
    h1_m = _RE_H1.search(html)
    nome = _RE_TAG.sub("", h1_m.group(1)).strip() if h1_m else ""

    # Marca
    brand_m = _RE_BRAND.search(html)
    marca   = brand_m.group(1) if brand_m else ""

    # Preços
    strongs      = _RE_STRONG.findall(html)
    preco_pix    = strongs[0] if strongs else ""
    preco_cartao = strongs[1] if len(strongs) > 1 else preco_pix

    todos = _RE_PRECO.findall(html)
    uniq  = list(dict.fromkeys(p.replace(" ", "") for p in todos))
    preco_sem_desc = todos[1] if len(uniq) >= 3 else ""

    desc_m   = _RE_DESCONTO.search(html)
    desconto = f"-{desc_m.group(1)}%" if desc_m else ""

    # Disponibilidade: botão "Avise-me" indica produto indisponível
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
    def _links_da_pagina(html: str) -> set:
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
            if not html:
                break
            novos = _links_da_pagina(html)
            if not novos:
                break
            links |= novos
            page  += 1
        return links

    resultados = await asyncio.gather(*[_paginar(c) for c in CATS])
    return set().union(*resultados)

async def producer(client, sem, links, queue):
    async def _dl(url):
        async with sem:
            html = await fetch(client, url)
        await queue.put(html)

    await asyncio.gather(*[_dl(u) for u in links])
    await queue.put(None)   # sentinel


async def consumer(queue, executor):
    loop, rows = asyncio.get_running_loop(), []
    while True:
        html = await queue.get()
        if html is None:
            break
        result = await loop.run_in_executor(executor, parse_html, html)
        if result:
            rows.append(result)
    return rows

async def main():
    sem    = asyncio.Semaphore(SEM_DL)
    limits = httpx.Limits(max_connections=SEM_DL + 20,
                          max_keepalive_connections=SEM_DL,
                          keepalive_expiry=30)

    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT,
                                 limits=limits) as client:
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
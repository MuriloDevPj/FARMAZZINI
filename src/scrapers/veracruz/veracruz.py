import asyncio
import csv
import json
import multiprocessing
import os
import re
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

# ── Configurações ──────────────────────────────────────────────────────────────
BUCKET_NAME = "farmazzini-equipe6"
BASE        = "https://www.drogariaveracruz.com.br"
CATS        = [f"{BASE}/medicamentos/", f"{BASE}/generico/"]
RETRIES     = 3

_EM_LAMBDA = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
WORKERS    = 4 if _EM_LAMBDA else max(2, multiprocessing.cpu_count() - 1)

# Semáforo duplo:
#   SEM_CAT  — downloads de páginas de categoria (leve, HTML pequeno)
#   SEM_PROD — downloads de produto simultâneos
#              Cada HTML ~300KB → 150 simultâneos ≈ 45MB pico de fila
#              t3.micro tem 1GB → sobra ~800MB para o resto do processo
SEM_CAT  = 50
SEM_PROD = 150

COLS = ["ean", "nome", "marca", "preco_sem_desconto",
        "preco_pix", "preco_cartao", "desconto", "disponivel", "farmacia"]

HEADERS = {
    "User-Agent":                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language":           "pt-BR,pt;q=0.9",
    "Accept-Encoding":           "gzip, deflate, br",
    "Sec-Ch-Ua":                 '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile":          "?0",
    "Sec-Ch-Ua-Platform":        '"Windows"',
    "Sec-Fetch-Dest":            "document",
    "Sec-Fetch-Mode":            "navigate",
    "Sec-Fetch-Site":            "none",
    "Sec-Fetch-User":            "?1",
    "Upgrade-Insecure-Requests": "1",
}

_RE_JSONLD       = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
_RE_EAN_SCRIPT   = re.compile(r'"(?:gtin1[34]|gtin8|ean|eanCode|barcode)"\s*:\s*"(\d{8,14})"', re.I)
_RE_INDISPONIVEL = re.compile(r'Avise[\s-]*me', re.I)
_RE_LINK_HREF    = re.compile(r'href=["\']([^"\']+/p)["\']', re.I)
_RE_LINK_JSON    = re.compile(r'"link"\s*:\s*"(/[^"]+/p)"', re.I)
_RE_TOTAL        = re.compile(r'"totalCount"\s*:\s*(\d+)', re.I)
_RE_PAG_TEXTO    = re.compile(r'(\d[\d.]*)\s+resultado', re.I)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_out_file() -> Path:
    nome = f"veracruz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if _EM_LAMBDA:
        return Path("/tmp") / nome
    local_win = Path(r"C:\Users\muril\Documents\TrienamentoPJ\T1\FARMAZZINI\data\raw") / nome
    if local_win.parent.exists():
        return local_win
    try:
        p = Path(__file__).resolve().parents[3] / "data" / "raw" / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    except (IndexError, OSError):
        return Path.cwd() / nome

def _txt(tag) -> str:
    return tag.get_text(strip=True) if tag else ""

def _oculto(tag) -> bool:
    return "display:none" in (tag.get("style", "").replace(" ", "")) if tag else True

def _limpa_preco(texto: str) -> str:
    m = re.search(r'R\$\s*[\d.,]+', texto)
    return m.group(0) if m else ""

def _float(texto: str) -> float:
    try:
        return float(re.sub(r'[^\d,]', '', texto).replace(',', '.'))
    except (ValueError, AttributeError):
        return 0.0

def enviar_para_s3(caminho_local: Path) -> None:
    try:
        import boto3
        boto3.client("s3").upload_file(
            str(caminho_local), BUCKET_NAME, f"raw/{caminho_local.name}"
        )
    except Exception:
        pass


# ── Parse (CPU-bound, roda no executor) ───────────────────────────────────────

def parse_html(html: str) -> dict | None:
    if not html or len(html) < 500:
        return None

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

    soup    = BeautifulSoup(html, "lxml")
    content = soup.select_one("#content-product")
    if not content:
        return None

    nome  = _txt(content.select_one("h1"))
    marca = _txt(content.select_one("h1 + div a, h1 ~ div a"))

    seal         = content.select_one(".seal-pix strong, .sale-price-pix strong")
    preco_pix    = _limpa_preco(_txt(seal)) if seal else ""
    prices_div   = content.select_one(".prices")
    cartao_tag   = prices_div.select_one(".sale-price strong") if prices_div else None
    preco_cartao = _limpa_preco(_txt(cartao_tag)) if cartao_tag else ""

    if not preco_pix:
        preco_pix = preco_cartao

    unit_tag       = prices_div.select_one(".unit-price") if prices_div else None
    preco_sem_desc = (_limpa_preco(_txt(unit_tag))
                      if (unit_tag and not _oculto(unit_tag)) else preco_cartao)

    desc_tag = prices_div.select_one(".descont") if prices_div else None
    desconto = (_txt(desc_tag)
                if (desc_tag and not _oculto(desc_tag) and _txt(desc_tag) != "0%") else "")

    inst_div = content.select_one(".card-installments")
    n_tag    = inst_div.select_one(".get_min_installments") if inst_div else None
    val_tag  = inst_div.select_one(".get_card_price")       if inst_div else None
    if n_tag and val_tag:
        n            = int(re.sub(r'\D', '', _txt(n_tag)) or 1)
        preco_cartao = (f"R$ {n * _float(_txt(val_tag)):,.2f}"
                        .replace(",","X").replace(".",",").replace("X","."))
    elif val_tag and not n_tag:
        preco_cartao = _limpa_preco(_txt(val_tag))

    disponivel = "Indisponível" if _RE_INDISPONIVEL.search(html) else "Disponível"

    return dict(ean=ean, nome=nome, marca=marca,
                preco_sem_desconto=preco_sem_desc, preco_pix=preco_pix,
                preco_cartao=preco_cartao, desconto=desconto,
                disponivel=disponivel, farmacia="Vera Cruz")


# ── I/O assíncrono ─────────────────────────────────────────────────────────────

async def fetch(session: AsyncSession, url: str, sem: asyncio.Semaphore) -> str:
    async with sem:
        for attempt in range(RETRIES):
            try:
                r = await session.get(url, impersonate="chrome124",
                                      headers=HEADERS, allow_redirects=True, timeout=20)
                r.raise_for_status()
                return r.text
            except Exception:
                if attempt < RETRIES - 1:
                    await asyncio.sleep(1.5 ** attempt)
    return ""


def _extrair_links(html: str) -> set:
    links = set()
    for href in _RE_LINK_HREF.findall(html):
        links.add(href if href.startswith("http") else BASE + href)
    for path in _RE_LINK_JSON.findall(html):
        links.add(BASE + path)
    return links


def _total_paginas(html: str, por_pagina: int = 20) -> int:
    m = _RE_TOTAL.search(html)
    if m:
        return max(1, -(-int(m.group(1)) // por_pagina))
    m = _RE_PAG_TEXTO.search(html)
    if m:
        return max(1, -(-int(m.group(1).replace(".", "")) // por_pagina))
    nums = re.findall(r'[?&]p=(\d+)', html)
    return max([int(n) for n in nums], default=1)


async def coletar_links(session: AsyncSession) -> set:
    sem = asyncio.Semaphore(SEM_CAT)

    async def _cat(base_url: str) -> set:
        html_p1    = await fetch(session, f"{base_url}?p=1", sem)
        if not html_p1:
            return set()
        total_pags = _total_paginas(html_p1)
        extras     = await asyncio.gather(*[
            fetch(session, f"{base_url}?p={p}", sem)
            for p in range(2, total_pags + 1)
        ])
        links = _extrair_links(html_p1)
        for html in extras:
            links |= _extrair_links(html)
        return links

    return set().union(*await asyncio.gather(*[_cat(c) for c in CATS]))


async def main_async() -> Path:
    print("Iniciando extracao Vera Cruz...")

    sem_prod = asyncio.Semaphore(SEM_PROD)
    loop     = asyncio.get_running_loop()
    out      = _resolve_out_file()
    out.parent.mkdir(parents=True, exist_ok=True)

    ExecutorClass = ThreadPoolExecutor if _EM_LAMBDA else ProcessPoolExecutor

    async with AsyncSession() as session:
        links = await coletar_links(session)

        with ExecutorClass(max_workers=WORKERS) as executor:
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=COLS)
                writer.writeheader()

                # ── Arquitetura: producer/consumer com semáforo ──────────────
                # O semáforo SEM_PROD garante que no máximo 150 HTMLs existem
                # na memória ao mesmo tempo. Assim todos os fetches correm em
                # paralelo real, sem chunks sequenciais, sem OOM.
                # O asyncio.as_completed garante que cada resultado é gravado
                # e descartado assim que fica pronto, liberando a memória.

                queue_parse: asyncio.Queue = asyncio.Queue()

                async def _fetch_and_enqueue(url: str) -> None:
                    html = await fetch(session, url, sem_prod)
                    await queue_parse.put(html)

                async def _producer() -> None:
                    await asyncio.gather(*[_fetch_and_enqueue(u) for u in links])
                    await queue_parse.put(None)  # sentinel

                async def _consumer() -> None:
                    while True:
                        html = await queue_parse.get()
                        if html is None:
                            break
                        # Despacha parse para o executor sem bloquear o loop
                        row = await loop.run_in_executor(executor, parse_html, html)
                        if row:
                            writer.writerow(row)
                        # HTML já pode ser coletado pelo GC
                        del html

                prod_task = asyncio.create_task(_producer())
                await _consumer()
                await prod_task

    enviar_para_s3(out)
    print("Extracao Vera Cruz concluida.")
    return out


def lambda_handler(event, context):
    asyncio.run(main_async())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    asyncio.run(main_async())
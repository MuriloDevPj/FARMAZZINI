import asyncio
import csv
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

# ── Configurações ──────────────────────────────────────────────────────────────
BUCKET_NAME = "farmazzini-equipe6"
BASE        = "https://www.farmaponte.com.br"
CATS        = [f"{BASE}/saude/medicamentos/"]
RETRIES     = 3
WORKERS     = 8

SEM_CAT  = 50
SEM_PROD = 150

COLS = ["ean", "nome", "marca", "preco_sem_desconto",
        "preco_pix", "preco_cartao", "desconto", "disponivel",
        "cashback", "desconto_especial", "farmacia"]

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
    "Referer":                   f"{BASE}/",
}

_RE_JSONLD     = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
_RE_EAN_SCRIPT = re.compile(r'"(?:gtin1[34]|gtin8|ean|eanCode|barcode)"\s*:\s*"(\d{8,14})"', re.I)
_RE_PAGINAS    = re.compile(r'de\s+(\d+)', re.I)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_out_file() -> Path:
    nome = f"farmaponte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return Path("/tmp") / nome
    local_win = Path(r"C:\Users\muril\Documents\TrienamentoPJ\T1\FARMAZZINI\data\raw") / nome
    if local_win.parent.exists():
        return local_win
    return Path.cwd() / nome

def _txt(tag) -> str:
    return tag.get_text(strip=True) if tag else ""

def _limpa_preco(texto: str) -> str:
    m = re.search(r'R\$\s*[\d.,]+', str(texto))
    return m.group(0) if m else ""

def _float(texto: str) -> float:
    try:
        return float(re.sub(r'[^\d,]', '', str(texto)).replace(',', '.'))
    except (ValueError, AttributeError):
        return 0.0

def _fmt(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def enviar_para_s3(caminho_local: Path) -> None:
    try:
        import boto3
        boto3.client("s3").upload_file(
            str(caminho_local), BUCKET_NAME, f"raw/{caminho_local.name}"
        )
    except Exception:
        pass


# ── Parse (CPU-bound, roda no executor) ───────────────────────────────────────

def parse_html(html: str, cashback: str = "") -> dict | None:
    """
    Recebe o HTML da página do produto e o cashback já extraído
    da página de listagem.
    """
    if not html or len(html) < 500:
        return None

    # ── EAN ──────────────────────────────────────────────────────────────────
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

    soup = BeautifulSoup(html, "lxml")

    # ── Dados básicos ─────────────────────────────────────────────────────────
    nome  = _txt(soup.select_one("h1.name") or soup.select_one("h1"))
    marca = _txt(soup.select_one("a.title_marca, .title_marca"))

    preco_sem_desc   = _limpa_preco(_txt(soup.select_one("p.unit-price, .unit-price")))
    pix_el           = soup.select_one("p.seal-pix.sale-price-pix, p.sale-price-pix")
    preco_pix        = _limpa_preco(_txt(pix_el))
    parcelas_el      = soup.select_one("strong.get_min_installments")
    valor_parcela_el = soup.select_one("strong.get_card_price")
    preco_cartao     = ""

    if parcelas_el and valor_parcela_el:
        n_m = re.search(r'\d+', _txt(parcelas_el))
        n   = int(n_m.group()) if n_m else 1
        val = _float(_txt(valor_parcela_el))
        if val:
            preco_cartao = _fmt(n * val)
    elif valor_parcela_el:
        preco_cartao = _limpa_preco(_txt(valor_parcela_el))

    if not preco_pix:      preco_pix      = preco_cartao
    if not preco_sem_desc: preco_sem_desc = preco_cartao

    pf         = _float(preco_sem_desc)
    pt         = _float(preco_pix)
    desconto   = f"{round((1 - pt / pf) * 100)}%" if pf > 0 and 0 < pt < pf else "0%"
    disponivel = "Disponível" if preco_pix else "Indisponível"

    # ── Cashback ──────────────────────────────────────────────────────────────
    # Recebido como parâmetro — extraído do card na página de listagem.
    # Fallback: tenta o elemento na página do produto (nem sempre presente).
    if not cashback:
        cashback_el = soup.select_one("strong.loyalty_price")
        if cashback_el:
            cashback = _limpa_preco(_txt(cashback_el))

    # ── Desconto especial ─────────────────────────────────────────────────────
    desconto_especial = ""

    # Tipo 1: Leve X Pague Y  →  <span class="seal-leve-x-pague-y" buy="3" pay="2">
    leve_pague_el = soup.select_one("span.seal-leve-x-pague-y")
    if leve_pague_el:
        buy = leve_pague_el.get("buy", "")
        pay = leve_pague_el.get("pay", "")
        if buy and pay:
            desconto_especial = f"Leve {buy} Pague {pay}"
        else:
            txt = _txt(leve_pague_el)
            if txt:
                desconto_especial = txt

    # Tipo 2: Compre junto / quantidade mínima
    # <div class="seal seal_discont buy-together" data-qtd="3" data-buy="None">
    #   <b>A PARTIR DE 3 UNIDADES, PAGUE R$ 10,24 CADA</b>
    # </div>
    if not desconto_especial:
        buy_together_el = soup.select_one("div.seal_discont.buy-together")
        if buy_together_el:
            qtd = buy_together_el.get("data-qtd", "")
            txt = _txt(buy_together_el.select_one("b") or buy_together_el)
            if txt:
                desconto_especial = txt
            elif qtd:
                desconto_especial = f"A partir de {qtd} unidades"

    return dict(
        ean=ean, nome=nome, marca=marca,
        preco_sem_desconto=preco_sem_desc, preco_pix=preco_pix,
        preco_cartao=preco_cartao, desconto=desconto,
        disponivel=disponivel, cashback=cashback,
        desconto_especial=desconto_especial, farmacia="FarmaPonte"
    )


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


async def coletar_links(session: AsyncSession) -> dict[str, str]:
    """
    Retorna um dict {url_produto: cashback} extraindo o cashback
    diretamente do card na página de listagem.
    """
    sem = asyncio.Semaphore(SEM_CAT)

    async def _cat(base_url: str) -> dict[str, str]:
        html_p1 = await fetch(session, base_url, sem)
        if not html_p1:
            return {}

        # Descobre número de páginas
        soup  = BeautifulSoup(html_p1, "lxml")
        max_p = 1
        pag_t = soup.find(string=_RE_PAGINAS)
        if pag_t:
            m = _RE_PAGINAS.search(str(pag_t))
            if m:
                max_p = int(m.group(1))

        extras = await asyncio.gather(*[
            fetch(session, f"{base_url}?p={i}", sem)
            for i in range(2, max_p + 1)
        ])

        resultado: dict[str, str] = {}
        for html in [html_p1] + list(extras):
            s = BeautifulSoup(html, "lxml")
            for card in s.select("div.item-product"):
                # URL do produto
                a = card.select_one("a.item-image")
                if not a:
                    continue
                href = a.get("href", "")
                if not href.endswith("/p"):
                    continue
                url = href if href.startswith("http") else BASE + href

                # Cashback do card
                cb_el    = card.select_one("strong.loyalty_price")
                cashback = _limpa_preco(_txt(cb_el)) if cb_el else ""

                resultado[url] = cashback

        return resultado

    dicts = await asyncio.gather(*[_cat(c) for c in CATS])
    merged: dict[str, str] = {}
    for d in dicts:
        merged.update(d)
    return merged


async def main_async() -> Path:
    print("Iniciando extracao FarmaPonte...")

    sem_prod = asyncio.Semaphore(SEM_PROD)
    loop     = asyncio.get_running_loop()
    out      = _resolve_out_file()
    out.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSession() as session:
        # links agora é dict {url: cashback}
        links = await coletar_links(session)
        print(f"Links coletados: {len(links)}")

        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=COLS)
                writer.writeheader()

                # Fila carrega tuplas (html, cashback)
                queue_parse: asyncio.Queue = asyncio.Queue()

                async def _fetch_and_enqueue(url: str, cashback: str) -> None:
                    html = await fetch(session, url, sem_prod)
                    await queue_parse.put((html, cashback))

                async def _producer() -> None:
                    await asyncio.gather(*[
                        _fetch_and_enqueue(url, cashback)
                        for url, cashback in links.items()
                    ])
                    await queue_parse.put(None)  # sentinel

                async def _consumer() -> None:
                    while True:
                        item = await queue_parse.get()
                        if item is None:
                            break
                        html, cashback = item
                        row = await loop.run_in_executor(
                            executor, parse_html, html, cashback
                        )
                        if row:
                            writer.writerow(row)
                        del html

                prod_task = asyncio.create_task(_producer())
                await _consumer()
                await prod_task

    enviar_para_s3(out)
    print("Extracao FarmaPonte concluida.")
    return out


def lambda_handler(event, context):
    asyncio.run(main_async())


if __name__ == "__main__":
    asyncio.run(main_async())
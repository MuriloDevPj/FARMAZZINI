import logging
import os
import time
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
import requests

# ===========================================================================
# CONFIGURAÇÃO E IDENTIDADE
# ===========================================================================

BASE_URL = "https://www.drogariaveracruz.com.br"
OUTPUT_FILE = "src/scrapers/veracruz/urls_veracruz.txt"
PRODUCT_SUFFIX = "/p"

# Filtros para garantir que pegamos apenas Medicamentos
KEYWORDS_MEDICAMENTOS = [
    "/medicamentos", "/genericos", "/diabetes", 
    "/pressao-alta", "/dor-e-febre", "/antibioticos"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("VeraCruzCollector")

# ===========================================================================
# NÚCLEO DE COLETA
# ===========================================================================

@dataclass
class HttpClient:
    delay: float = 0.5
    timeout: tuple = (10, 25)

    def get(self, url: str) -> requests.Response | None:
        try:
            response = requests.get(url, headers=HEADERS, timeout=self.timeout)
            if response.status_code == 200:
                time.sleep(self.delay)
                return response
        except Exception as e:
            log.error(f"  ❌ Erro ao acessar {url}: {e}")
        return None

class VeraCruzURLCollector:
    def __init__(self):
        self.client = HttpClient()
        self.urls_medicamentos = []

    def extrair_links(self, xml_text):
        """Extrai URLs de produtos e sub-sitemaps de forma abrangente."""
        try:
            root = ET.fromstring(xml_text.strip().lstrip("\ufeff"))
            urls = [el.text.strip() for el in root.iter() if el.tag.endswith('loc') and el.text]
            
            # Mudança estratégica: 
            # Pegamos TODOS que terminam em /p. 
            # O filtro de 'o que é medicamento' faremos na extração de dados.
            filtrados = [u for u in urls if u.endswith(PRODUCT_SUFFIX)]
            
            sub_sitemaps = [u for u in urls if "sitemap" in u.lower()]
            return filtrados, sub_sitemaps
        except Exception:
            return [], []

    def executar(self):
        log.info("=" * 60)
        log.info("🛰️  INICIANDO COLETA FILTRADA: DROGARIA VERA CRUZ")
        log.info("=" * 60)

        # Passo 1: Descobrir sitemap via robots.txt
        log.info("🤖 Lendo robots.txt...")
        resp = self.client.get(f"{BASE_URL}/robots.txt")
        if not resp: return

        sitemap_raiz = next((line.split(": ")[1] for line in resp.text.splitlines() if "sitemap" in line.lower()), None)
        
        if sitemap_raiz:
            log.info(f"📍 Sitemap Index encontrado: {sitemap_raiz}")
            
            # Passo 2: Processar o Index
            resp_index = self.client.get(sitemap_raiz)
            if resp_index:
                _, sub_sitemaps = self.extrair_links(resp_index.text)
                
                # Passo 3: Percorrer sub-sitemaps
                for sub in sub_sitemaps:
                    log.info(f"📂 Processando: {sub.split('/')[-1]}")
                    r_sub = self.client.get(sub)
                    if r_sub:
                        links, _ = self.extrair_links(r_sub.text)
                        self.urls_medicamentos.extend(links)
                        log.info(f"   ✨ {len(links)} medicamentos encontrados nesta parte.")

        # Passo 4: Salvar e Finalizar
        self.urls_medicamentos = list(dict.fromkeys(self.urls_medicamentos))
        if self.urls_medicamentos:
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.writelines(f"{u}\n" for u in self.urls_medicamentos)
            
            log.info("=" * 60)
            log.info(f"✅ SUCESSO: {len(self.urls_medicamentos)} MEDICAMENTOS SALVOS.")
            log.info(f"📁 ARQUIVO: {OUTPUT_FILE}")
            log.info("=" * 60)

if __name__ == "__main__":
    collector = VeraCruzURLCollector()
    collector.executar()
import re
import pandas as pd
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class VeraCruz:
    def __init__(self):
        self.farmacia = "Vera Cruz"
        self.driver = self._configurar_driver()

    def _configurar_driver(self):
        chrome_options = Options()
        # Headless é essencial para processamento em massa (ganha velocidade)
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--log-level=3") # Silencia avisos inúteis do Chrome
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    def extrair_produto(self, url):
        try: 
            self.driver.get(url)
            time.sleep(2) # Tempo para o JS carregar preços e breadcrumb

            # --- 1. FILTRO DE CATEGORIA (BREADCRUMB) ---
            try:
                # Usando o ID 'breadcrumb' identificado no seu print
                breadcrumb_txt = self.driver.find_element(By.ID, "breadcrumb").text.lower()
                alvos = ["medicamentos", "genéricos", "saúde", "diabetes", "hipertensão"]
                
                if not any(p in breadcrumb_txt for p in alvos):
                    return "PULAR" 
            except:
                return None 

            # --- 2. EXTRAÇÃO DOS DADOS BÁSICOS ---
            nome = self.driver.find_element(By.XPATH, '//*[@id="content-product"]/div/div/div[2]/h1').text
            try:
                marca = self.driver.find_element(By.XPATH, '//*[@id="content-product"]/div/div/div[2]/div[2]/a[1]').text
            except:
                marca = "N/A"
            
            # --- 3. EXTRAÇÃO DE PREÇOS (TRATAMENTO DE ERRO) ---
            try:
                preco_pix = self.driver.find_element(By.XPATH, '//strong[contains(text(), "R$")]').text
                preco_regular = self.driver.find_element(By.XPATH, '//p[contains(@class, "price-regular")]/del').text
                preco_cartao = self.driver.find_element(By.XPATH, '//p[contains(@class, "price-card")]/strong').text
                desconto = self.driver.find_element(By.XPATH, '//span[contains(@class, "discount")]').text
            except:
                preco_pix = preco_regular = preco_cartao = desconto = "Consultar Site"

            # --- 4. EAN VIA REGEX (MAIS ROBUSTO) ---
            try:
                html = self.driver.page_source
                ean_match = re.search(r'"gtin13":\s*"(\d+)"', html)
                ean = ean_match.group(1) if ean_match else "N/A"
            except:
                ean = "N/A"

            disponibilidade = "Disponível" if "http://schema.org/InStock" in self.driver.page_source else "Fora de Estoque"

            return {
                "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                "farmacia": self.farmacia,
                "ean": ean,
                "produto": nome,
                "marca": marca,
                "preco_regular": preco_regular,
                "preco_pix": preco_pix,
                "preco_cartao": preco_cartao,
                "desconto": desconto,
                "status_estoque": disponibilidade,
                "url": url
            }
        except Exception as e:
            return None

    def fechar(self):
        self.driver.quit()

# ===========================================================================
# ORQUESTRADOR DE EXECUÇÃO
# ===========================================================================

def iniciar_automacao():
    input_file = "src/scrapers/veracruz/urls_veracruz.txt"
    output_file = "src/scrapers/veracruz/coleta_veracruz.csv"
    
    if not os.path.exists(input_file):
        print("❌ Arquivo de URLs não encontrado!")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f.readlines()]

    scraper = VeraCruz()
    resultados = []
    total = len(urls)

    print(f"🚀 Processando {total} links. Somente medicamentos serão salvos.")
    print("Pressione Ctrl+C para parar e salvar o progresso atual.\n")

    try:
        for i, url in enumerate(urls, 1):
            res = scraper.extrair_produto(url)
            
            if res == "PULAR":
                print(f"⏩ [{i}/{total}] Ignorado (Perfumaria)")
                continue
            
            if res:
                resultados.append(res)
                print(f"✅ [{i}/{total}] Coletado: {res['produto'][:30]}...")
            
            # Salvamento de segurança a cada 25 itens
            if i % 25 == 0 and resultados:
                pd.DataFrame(resultados).to_csv(output_file, index=False, encoding="utf-8-sig")
                print(f"💾 Checkpoint: {len(resultados)} itens salvos...")

    except KeyboardInterrupt:
        print("\n\n🛑 Interrupção detectada! Salvando dados coletados...")
    finally:
        if resultados:
            pd.DataFrame(resultados).to_csv(output_file, index=False, encoding="utf-8-sig")
            print(f"\n🏁 CONCLUÍDO! Total extraído: {len(resultados)}")
            print(f"📁 Arquivo: {output_file}")
        scraper.fechar()

if __name__ == "__main__":
    iniciar_automacao()







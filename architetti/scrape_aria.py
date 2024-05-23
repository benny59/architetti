import logging
import os
import platform
import sqlite3
from hashlib import md5
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from io import StringIO  # Importato per gestire il warning di Pandas

# Importa le funzioni dal file architetti.py

def get_chromedriver_path():
    if platform.system() == 'Linux':
        if os.path.isfile('/usr/local/bin/chromedriver'):
            return '/usr/local/bin/chromedriver'
        elif os.path.isfile('/usr/bin/chromedriver'):
            return '/usr/bin/chromedriver'
    elif platform.system() == 'Darwin':  # MacOS
        return '/usr/local/bin/chromedriver'
    elif platform.system() == 'Windows':
        return 'C:\\path\\to\\chromedriver.exe'  # Aggiorna questo percorso con il percorso corretto per Windows
    raise Exception("Chromedriver not found. Please ensure chromedriver is installed and the path is correct.")

def get_chrome_binary_location():
    if platform.system() == 'Linux':
        if os.path.isfile('/usr/bin/google-chrome-stable'):
            return '/usr/bin/google-chrome-stable'
        elif os.path.isfile('/usr/bin/chromium-browser'):
            return '/usr/bin/chromium-browser'
    elif platform.system() == 'Darwin':  # MacOS
        return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    elif platform.system() == 'Windows':
        return 'C:\\path\\to\\chrome.exe'  # Aggiorna questo percorso con il percorso corretto per Windows
    raise Exception("Chrome binary not found. Please ensure Chrome is installed and the path is correct.")

def scrape_aria(db_file, url):
    from architetti import record_exists, insert_record  # Importazione locale per evitare circular import

    try:
        chromedriver_path = get_chromedriver_path()
        chrome_binary_location = get_chrome_binary_location()

        service = Service(chromedriver_path)
        options = Options()
        options.binary_location = chrome_binary_location
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        try:
            # Clicca il pulsante 'SEDE LEGALE'
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'regionSua'))).click()
            logging.debug("Pulsante 'SEDE LEGALE' cliccato")

            # Deseleziona 'Tutte'
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'j_idt28:j_idt31:auctionLegalSite:0'))).click()
            logging.debug("Opzione 'Tutte' deselezionata")

            # Seleziona 'Regione Liguria'
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'j_idt28:j_idt31:auctionLegalSite:5'))).click()
            logging.debug("Opzione 'Regione Liguria' selezionata")

            # Applica i filtri
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'j_idt28:j_idt31:template-contactform-submit'))).click()
            logging.debug("Filtri applicati")

            # Aspetta che i risultati vengano caricati
            sleep(5)
            
             # Esegui JavaScript per ordinare per "DATA FINE"
            logging.debug("Ordinamento per 'DATA FINE' eseguito")
            driver.execute_script(
                "mojarra.jsfcljs(document.getElementById('j_idt154:j_idt165'),"
                "{'j_idt154:j_idt165:j_idt167:10:j_idt177':'j_idt154:j_idt165:j_idt167:10:j_idt177'},'');"
                "return false;"
            )
            sleep(1)
            driver.execute_script(
                "mojarra.jsfcljs(document.getElementById('j_idt154:j_idt165'),"
                "{'j_idt154:j_idt165:j_idt167:10:j_idt177':'j_idt154:j_idt165:j_idt167:10:j_idt177'},'');"
                "return false;"
            )


            # Usa JavaScript per impostare il valore del menu a discesa degli elementi per pagina
            driver.execute_script("document.getElementsByName('j_idt154:j_idt226:j_idt237')[0].value = '200';")
            driver.execute_script("document.getElementsByName('j_idt154:j_idt226:j_idt237')[0].dispatchEvent(new Event('change'));")
            logging.debug("Selezionato 100 elementi per pagina")

            # Raccogli i dati
            sleep(5)  # Attendi il caricamento dei nuovi dati
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'result'))
            )



            # Estrai i dati dalla tabella
            df = pd.read_html(StringIO(table.get_attribute('outerHTML')))[0]

            # Stampa la struttura della tabella per verifica
            #print(df.columns)

            # Adatta la specifica delle colonne
            df.columns = ['ID SINTEL', 'STAZIONE APPALTANTE', 'NOME PROCEDURA', 'CODICE GARA', 'TIPO', 'STATO', 'AMBITO DELLA PROCEDURA', 'VALORE ECONOMICO', 'DATA INIZIO', 'DATA FINE RICEZIONE OFFERTE']

            new_records = []

            for index, row in df.iterrows():
                record = {
                    'title': row['STAZIONE APPALTANTE'],
                    'date': row['DATA FINE RICEZIONE OFFERTE'],
                    'category': row['TIPO'],
                    'summary': row['NOME PROCEDURA'],
                    'url': f"https://www.sintel.regione.lombardia.it/eprocdata/auctionDetail.xhtml?id={row['ID SINTEL']}",
                    'checksum': md5(str(row['ID SINTEL']).encode('utf-8')).hexdigest()
                }

                table_name = "records_aria"
                if not record_exists(db_file, table_name, record['checksum']):
                    insert_record(db_file, table_name, record)
                    new_records.append(record)

            driver.quit()
            return new_records

        except Exception as e:
            logging.error(f"Errore durante lo scraping: {e}")
            driver.quit()
            return []

    except Exception as e:
        logging.error(f"Errore durante l'inizializzazione di WebDriver: {e}")
        return []

# Le altre funzioni e il main restano invariati

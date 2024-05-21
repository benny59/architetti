import os
import time
import logging
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
from hashlib import md5

# Configurazione del logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_aria(db_file, url):
    new_records = []

    # Configura il servizio di ChromeDriver
    service = Service('/usr/local/bin/chromedriver')
    options = webdriver.ChromeOptions()
    options.binary_location = '/usr/bin/google-chrome-stable'

    # Avvia il driver di Selenium
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)

    try:
        # Attendi che il pulsante 'SEDE LEGALE' sia cliccabile e clicca
        legal_site_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'regionSua'))
        )
        legal_site_button.click()
        logging.info("Pulsante 'SEDE LEGALE' cliccato")

        # Attendi che l'opzione 'Tutte' sia visibile e deseleziona
        all_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Tutte')]/input"))
        )
        if all_option.is_selected():
            all_option.click()
            logging.info("Opzione 'Tutte' deselezionata")

        # Attendi che l'opzione 'Regione Liguria' sia visibile e clicca
        liguria_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Regione Liguria')]/input"))
        )
        liguria_option.click()
        logging.info("Opzione 'Regione Liguria' selezionata")

        # Invia il form per applicare i filtri
        apply_button = driver.find_element(By.NAME, 'j_idt28:j_idt31:template-contactform-submit')
        apply_button.click()
        logging.info("Filtri applicati")

        # Attendi che il menu a discesa degli elementi per pagina sia presente
        elements_per_page_dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "j_idt154:j_idt226:j_idt237"))
        )
        elements_per_page_dropdown.click()
        logging.info("Menu a discesa per elementi per pagina cliccato")

        # Seleziona 100 elementi per pagina
        elements_per_page_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//option[@value='100']"))
        )
        elements_per_page_option.click()
        logging.info("Selezionato 100 elementi per pagina")

        # Attendi che la pagina venga aggiornata
        WebDriverWait(driver, 10).until(
            EC.staleness_of(elements_per_page_option)
        )

        # Ricarica la tabella dopo aver cambiato il numero di elementi per pagina
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'result'))
        )
        logging.info("Tabella dei risultati caricata")

        # Ottieni il contenuto della pagina
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Trova la tabella
        table = soup.find('table', {'id': 'result'})

        # Estrai le intestazioni delle colonne
        headers = [header.text.strip() for header in table.find_all('th')]

        # Estrai i dati delle righe
        rows = []
        for row in table.find_all('tr'):
            cells = [cell.text.strip() for cell in row.find_all('td')]
            if cells:
                rows.append(cells)

        # Crea un DataFrame pandas
        df = pd.DataFrame(rows, columns=headers)

        # Verifica ogni record e aggiungi al database se non esiste
        table_name = "records_aria"
        for _, row in df.iterrows():
            url = f"https://www.sintel.regione.lombardia.it/eprocdata/auctionDetail.xhtml?id={row['ID SINTEL']}"
            record = {
                'title': row['STAZIONE APPALTANTE'],
                'date': row['DATA FINE'],
                'category': row['TIPO'],
                'summary': row['NOME PROCEDURA'],
                'url': url,
                'checksum': md5(row['NOME PROCEDURA'].encode('utf-8')).hexdigest()
            }
            if not record_exists(db_file, table_name, record['checksum']):
                insert_record(db_file, table_name, record)
                new_records.append(record)

    finally:
        # Chiudi il driver
        driver.quit()

    return new_records

# Funzioni di database esistenti
def insert_record(db_file, table_name, record):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(f'''INSERT INTO {table_name} (title, date, category, summary, url, checksum)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (record['title'], record['date'], record['category'], record['summary'], record['url'], record['checksum']))
    conn.commit()
    conn.close()

def record_exists(db_file, table_name, checksum):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(f'''SELECT * FROM {table_name} WHERE checksum = ?''', (checksum,))
    result = c.fetchone()
    conn.close()
    return result is not None

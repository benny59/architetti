import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_genova_concorsi(db_file, base_url):
    from architetti import record_exists, insert_record  # Importazione locale per evitare circular import
    results = []

    # Funzione per estrarre i record dalla pagina HTML
    def extract_records_from_page(soup):
        items = soup.select('div.viewport-container > div#ext-container.smooth-transition.page-container > div.container.two-columns-left-menu > div.columns > div.row > main.col-9 > div.responsive.content > div.portgare-list > form > div.list-item')
        page_results = []

        for item in items:
            def extract_text(label):
                element = item.find('label', string=lambda text: text and label in text)
                if element:
                    return element.find_next_sibling(text=True).strip()
                return 'Informazione non disponibile'

            def clean_text(text):
                return re.sub(r'\s+', ' ', text).strip()

            title = extract_text('Titolo :')
            category = extract_text('Tipologia appalto :')
            amount = extract_text('Importo :')
            publication_date = extract_text('Data pubblicazione :')
            expiration_date_raw = extract_text('Data scadenza :')
            expiration_date = clean_text(expiration_date_raw)

            procedure_reference = extract_text('Riferimento procedura :')
            status = extract_text('Stato :')
            detail_url_element = item.find('a', title='Visualizza scheda')
            detail_url = detail_url_element['href'] if detail_url_element else None

            # Normalizza i campi
            normalized_url = f"{detail_url}" if detail_url else 'URL non disponibile'

            try:
                if publication_date != 'Informazione non disponibile':
                    formatted_date = datetime.strptime(publication_date, '%d/%m/%Y').strftime('%Y-%m-%d')
                else:
                    formatted_date = 'Data non disponibile'
                
                if expiration_date != 'Informazione non disponibile':
                    formatted_expiration_date = f"{expiration_date}"
                else:
                    formatted_expiration_date = 'Data non disponibile'
            except ValueError as e:
                logging.error(f"Date parsing error: {e}")
                formatted_date = 'Data non disponibile'
                formatted_expiration_date = 'Data non disponibile'

            checksum = hashlib.md5(title.encode('utf-8')).hexdigest()

            result = {
                'Title': title,
                'Date': formatted_expiration_date,
                'Category': procedure_reference,
                'Description': amount,
                'Summary': amount,
                'URL': normalized_url,
                'Checksum': checksum,
                'ExpirationDate': formatted_expiration_date,
                'Status': status
            }
            #print(result)
            # Stampa i dettagli per il debug
            logging.debug(f"Record extracted: {result}")

            # Aggiungi solo record validi
            if title != 'Informazione non disponibile' and formatted_date != 'Data non disponibile':
                page_results.append(result)

        return page_results

    max_pages = 10
    page_num = 1
    while page_num <= max_pages:
        url = f"{base_url}&pag={page_num}"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        records = extract_records_from_page(soup)

        if not records:
            break

        for record in records:
            if not record_exists(db_file, 'records_genovaconcorsi', record['Checksum']):
                logging.debug(f"New record found: {record['Title']}")
                insert_record(db_file, 'records_genovaconcorsi', record)
                results.append(record)
            else:
                logging.debug(f"Record already exists: {record['Title']}")

        page_num += 1

    return results

# Esempio di utilizzo
if __name__ == '__main__':
    db_file = 'path/to/your/database/file.db'
    base_url = 'https://appalti.comune.genova.it/PortaleAppalti/it/homepage.wp?actionPath=/ExtStr2/do/FrontEnd/Bandi/view.action'
    logging.info("Starting scraping cycle...")
    results = scrape_genova_concorsi(db_file, base_url)
    for result in results:
        print(result)

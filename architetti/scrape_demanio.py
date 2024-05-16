import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_demanio(db_file, base_url):
    from architetti import record_exists, insert_record  # Importazione locale per evitare circular import
    results = []

    # Funzione per estrarre i record dalla pagina HTML
    def extract_records_from_page(soup):
        items = soup.select('div.col-sm-12.col-md-12.col-lg-6.mb-4')
        page_results = []

        for item in items:
            title_element = item.find('h2', class_='card-title')
            title = title_element.text.strip() if title_element else 'Informazione non disponibile'

            detail_url_element = title_element.find('a') if title_element else None
            detail_url = detail_url_element['href'] if detail_url_element else 'URL non disponibile'

            fields = {
                'cig': extract_text(item, 'CIG:'),
                'region': extract_text(item, 'Regione:'),
                'comune': extract_text(item, 'Comune:'),
                'tipo_procedura': extract_text(item, 'Tipo procedura:'),
                'oggetto_gara': extract_text(item, 'Oggetto della gara:'),
                'data_pubblicazione': extract_text(item, 'Data Pubblicazione bando:'),
                'termine_partecipazione': extract_text(item, 'Termine per partecipare:'),
                'descrizione': extract_description(item)
            }
            #print(fields)
            # Log per debug
            logging.debug(f"Extracted fields: {fields}")

            # Mappa correttamente i campi
            category = fields['oggetto_gara']
            summary = fields['descrizione']
            date = fields['termine_partecipazione'].split(' ', 4)[:3]

            try:
                formatted_pubblicazione = parse_date(fields['data_pubblicazione'])
                formatted_date = parse_date(" ".join(date))
            except ValueError as e:
                logging.error(f"Date parsing error: {e}")
                formatted_pubblicazione = 'Data non disponibile'
                formatted_date = 'Data non disponibile'

            checksum = hashlib.md5(title.encode('utf-8')).hexdigest()

            result = {
                'Title': title,
                'Date': fields['termine_partecipazione'],
                'Category': f"{category} {fields['region']} {fields['comune']} {fields['cig']}",
                'Description': summary,
                'Summary': summary,
                'URL': f"https://www.agenziademanio.it{detail_url}",
                'Checksum': checksum,
                'ExpirationDate': fields['termine_partecipazione'],
                'Status': 'In corso'
            }

            # Stampa i dettagli per il debug
            logging.debug(f"Record extracted: {result}")

            # Aggiungi solo record validi
            #if title != 'Informazione non disponibile' and formatted_pubblicazione != 'Data non disponibile':
            page_results.append(result)

        return page_results

    def extract_text(item, label):
        for p in item.find_all('p', class_='color_text_gare'):
            strong_tag = p.find('strong')
            if strong_tag and label in strong_tag.text:
                return p.text.replace(label, '').strip()
        return 'Informazione non disponibile'
        
    def extract_description(item):
        for p in item.find_all('p', class_='color_text_gare'):
            if 'Descrizione:' in p.text:
                skip_span = p.find('span', class_='skip')
                if skip_span:
                    skip_span.decompose()
                return p.text.strip().replace('Descrizione:', '').strip()
        return 'Informazione non disponibile'
 
    
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, '%d %B %Y').strftime('%Y-%m-%d')
        except ValueError:
            return 'Data non disponibile'

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
            # Converti tutti i valori del record in stringhe
            record = {key: str(value) for key, value in record.items()}

            if not record_exists(db_file, 'records_demanio', record['Checksum']):
                logging.debug(f"New record found: {record['Title']}")
                insert_record(db_file, 'records_demanio', record)
                results.append(record)
            else:
                logging.debug(f"Record already exists: {record['Title']}")

        page_num += 1

    return results

# Esempio di utilizzo
if __name__ == '__main__':
    db_file = 'path/to/your/database/file.db'
    base_url = 'https://www.agenziademanio.it/it/gare-aste/lavori/?garaFilters=r%3A07'
    logging.info("Starting scraping cycle...")
    results = scrape_demanio(db_file, base_url)
    for result in results:
        print(result)

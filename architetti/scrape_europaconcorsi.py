import os
import requests
from bs4 import BeautifulSoup
import logging
import hashlib

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def scrape_site(db_file, urls):
    if isinstance(urls, str):
        urls = [urls]

    new_records = []

    with requests.Session() as session:
        if login(session, "https://europaconcorsi.com/people/login"):
            for url in urls:
                try:
                    response = session.get(url)
                    if response.ok:
                        logging.info(f"Access to the page {url} successful")
                        records = extract_records(db_file, response.text)
                        if records:
                            logging.info(f"Data extracted successfully from {url}. Number of records: {len(records)}")
                            new_records.extend(records)
                        else:
                            logging.warning(f"No records found on the page {url}.")
                    else:
                        logging.error(f"Failed to access protected content at {url}. Status Code: {response.status_code}")
                except Exception as e:
                    logging.error(f"Errore durante lo scraping di {url}: {e}")
        else:
            logging.error("Login failed.")
    
    return new_records
    
def login(session, login_url):
    from architetti import get_config_value
    # Leggi le credenziali da variabili d'ambiente
    USERNAME = get_config_value('EUROPACONCORSI_USERNAME')
    PASSWORD = get_config_value('EUROPACONCORSI_PASSWORD')
	
    """Effettua il login al sito e ritorna True se il login è riuscito."""
    try:
        response = session.get(login_url)
        if response.status_code == 200:
            login_soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token_input = login_soup.find('input', {'name': 'authenticity_token'})
            if csrf_token_input and 'value' in csrf_token_input.attrs:
                csrf_token = csrf_token_input['value']
            else:
                logging.error("CSRF token not found on login page.")
                return False

            login_data = {
                'utf8': '✓',
                'person[email]': USERNAME,
                'person[password]': PASSWORD,
                'authenticity_token': csrf_token,
                'person[remember_me]': 'true'  # Aggiunto se vuoi che la sessione ricordi l'utente
            }

            # Invia i dati di login
            response = session.post(login_url, data=login_data)
            if response.ok:
                logging.info("Login successful")
                return True
            else:
                logging.error("Failed to log in: %s", response.text)
                return False
        else:
            logging.error(f"Failed to retrieve login page, status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        logging.error("Login error: %s", e)
        return False
def extract_records(db_file, html_content):
    from architetti import record_exists, insert_record  # Importazione locale per evitare circular import

    soup = BeautifulSoup(html_content, 'html.parser')
    records = []
    competitions = soup.find_all('div', class_='competition')

    for comp in competitions:
        permalink_element = comp.find('a', class_='permalink')
        url = "https://europaconcorsi.com" + permalink_element['href'] if permalink_element else None
        title = comp.find('div', class_='title').get_text(strip=True)
        place = comp.find('span', class_='place').get_text(strip=True).rstrip('·').strip()
        category=comp.find('span', class_='organization').get_text(strip=True).rstrip('·').strip()
        place = comp.find('span', class_='place').get_text(strip=True).rstrip('·').strip().upper()
        # Salta questo ciclo se 'place' non termina con ', Italia'
        if not place.endswith(', ITALIA'):
            continue

        checksum = hashlib.md5(title.encode('utf-8')).hexdigest()
        record = {
            'title': title,
            'place': place,
            'summary': " ".join(p.get_text(" ", strip=True) for p in comp.find('div', class_='description').find_all('p')),
            'category': category+' - '+place,
            'date': comp.find('span', class_='deadline').get_text(strip=True),
            'url': url,
            'checksum': checksum
        }
        if not record_exists(db_file, 'records_europaconcorsi', record['checksum']):
            logging.debug(f"New record found: {record['title']}")
            insert_record(db_file, 'records_europaconcorsi', record)
            records.append(record)
            print(record)
        else:
            logging.debug(f"Record already exists: {record['title']}")

    return records
    
    # Esempio di utilizzo
if __name__ == '__main__':
    db_file = 'path/to/your/database/file.db'
    scrape_url = 'https://europaconcorsi.com/bandi/partecipazione-ristretta'
    logging.info("Starting scraping cycle...")
    results = scrape_site(db_file, scrape_url)
    for result in results:
        print(result)

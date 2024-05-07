import os
import requests
from bs4 import BeautifulSoup
import logging
import sys

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Leggi le credenziali da variabili d'ambiente
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

def login(session, login_url):
    """Effettua il login al sito e ritorna True se il login è riuscito."""
    # Prima, recupera la pagina di login per ottenere il CSRF token
    login_page = session.get(login_url)
    login_soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = login_soup.find('input', {'name': 'authenticity_token'})['value']

    # Dati del form di login, includendo il CSRF token
    login_data = {
        'person[email]': USERNAME,
        'person[password]': PASSWORD,
        'authenticity_token': csrf_token
    }

    # Esegui la richiesta di login
    response = session.post(login_url, data=login_data)
    if response.ok:
        logging.info("Login successful")
        return True
    else:
        logging.error("Failed to log in")
        return False

def extract_records(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []
    competitions = soup.find_all('div', class_='competition')  # Ricerca di tutti i div con classe 'competition'

    for comp in competitions:
        # Estrazione del titolo
        title_element = comp.find('div', class_='title').find('a')
        title = title_element.get_text(strip=True) if title_element else "No title found"

        # Estrazione della descrizione
        description_element = comp.find('div', class_='description')
        description = " ".join(p.get_text(" ", strip=True) for p in description_element.find_all('p')) if description_element else "No description found"

        # Estrazione del link permanente
        permalink_element = comp.find('a', class_='permalink')
        link = "https://europaconcorsi.com" + permalink_element['href'] if permalink_element else None

        # Estrazione del link al file
        file_link_element = comp.find('a', class_='competition-link')
        file_link = file_link_element['href'] if file_link_element else None

        # Informazioni aggiuntive
        organization_element = comp.find('span', class_='organization')
        organization = organization_element.get_text(strip=True).rstrip('·').strip() if organization_element else "No organization found"

        place_element = comp.find('span', class_='place')
        place = place_element.get_text(strip=True).rstrip('·').strip() if place_element else "No place found"

        deadline_element = comp.find('span', class_='deadline')
        deadline = deadline_element.get_text(strip=True) if deadline_element else "No deadline found"

        # Costruzione del record
        record = {
            'Title': title,
            'Description': description,
            'Link': link,
            'File Link': file_link,
            'Organization': organization,
            'Place': place,
            'Deadline': deadline
        }
        records.append(record)
        #print(record)

    print_records_as_table(records)
    return records

from bs4 import BeautifulSoup
import requests



def scrape_site(session, page_url):
    """Esegue lo scraping del sito dopo il login e chiama extract_records per estrarre i dati."""
    # Assicurati di inserire l'URL corretto della pagina da cui stai cercando di estrarre i dati
    #url = "https://europaconcorsi.com/bandi/partecipazione-ristretta"
    #fetch_and_print_html(page_url)

    response = session.get(page_url)
    if response.ok:
        records = extract_records(response.text)  # Estrai i record utilizzando la funzione definita precedentemente
        if records:
            logging.info(f"Data extracted successfully. Number of records: {len(records)}")
            #print_records_as_table(records)  # Stampa i record come tabella
        else:
            logging.warning("No records found on the page.")
    else:
        logging.error(f"Failed to access protected content. Status Code: {response.status_code}")
        print(response.text)  # Stampa la risposta per vedere cosa c'è nella pagina

from tabulate import tabulate


from tabulate import tabulate

def print_records_as_table(records, max_width=120):  # Aumento la larghezza massima per adattarsi meglio al contenuto
    headers = ["Title", "Description", "Organization", "Place", "Deadline"]
    table_data = []

    # Adatta i dati e prepara le righe della tabella
    for record in records:
        # Estrai e prepara i dati da includere
        title = record.get('Title', 'N/A')
        description = record.get('Description', 'N/A')
        organization = record.get('Organization', 'N/A')
        place = record.get('Place', 'N/A')
        deadline = record.get('Deadline', 'N/A')

        # Aggiungi la riga alla tabella
        table_data.append([title, description, organization, place, deadline])

    # Stampa la tabella usando tabulate
    print(tabulate(table_data, headers=headers, tablefmt="grid", maxcolwidths=[30, 30, 30, 15, 15]))




def main():
    base_url = 'https://europaconcorsi.com'
    login_url = f'{base_url}/people/login'
    with requests.Session() as session:
        if login(session, login_url):
            scrape_site(session, f'{base_url}/bandi/partecipazione-ristretta')

if __name__ == "__main__":
    main()

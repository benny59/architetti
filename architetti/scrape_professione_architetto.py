import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import logging


def scrape_professione_architetto(db_file):
    from architetti import record_exists, insert_record  # Importazione locale per evitare circular import
    base_url = "https://www.professionearchitetto.it/key/concorsi-di-progettazione/"
    results = []

    # Funzione per estrarre i record da una pagina
    def extract_records_from_page(soup):
        base_url = "https://www.professionearchitetto.it"
        articles = soup.find_all('article', class_='addlink')
        page_results = []

        for article in articles:
            title_tag = article.find('h2', class_='entry-title')
            title = title_tag.text.strip()
            relative_url = title_tag.find('a')['href'] if title_tag.find('a') else None
            url = base_url + relative_url if relative_url else None  # Completa l'URL concatenando la parte base con l'URL relativo
            date = article.find('time', class_='date').text.strip()
            category = article.find('span', class_='categoria').text.strip()
            img_tag = article.find('img')
            image = img_tag['data-src'] if img_tag and 'data-src' in img_tag.attrs else None
            summary = article.find('div', class_='entry-summary').text.strip()

            # Calcola il checksum per identificare il record
            checksum = hashlib.md5(title.encode('utf-8')).hexdigest()

            result = {
                'Title': title,
                'Date': datetime.strptime(date, '%d.%m.%Y').strftime('%Y-%m-%d'),
                'Category': category,
                'Image': image,
                'Summary': summary,
                'URL': url,
                'Checksum': checksum
            }
            page_results.append(result)

        return page_results

    max_pages = 10
    page_num = 1
    while page_num <= max_pages:
        url = f"{base_url}?pag={page_num}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        records = extract_records_from_page(soup)

        if not records:
            break

        for record in records:
            if not record_exists(db_file, 'records_professione_architetto', record['Checksum']):
                logging.debug(f"New record found: {record['Title']}")
                insert_record(db_file, 'records_professione_architetto', record)
                results.append(record)
            else:
                logging.debug(f"Record already exists: {record['Title']}")

        page_num += 1

    return results

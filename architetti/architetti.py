import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import textwrap
from datetime import datetime

def create_database(db_file):
    if not os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS records
                     (id INTEGER PRIMARY KEY,
                     title TEXT,
                     date TEXT,
                     category TEXT,
                     summary TEXT,
                     appointment TEXT)''')  # Aggiunge la colonna "appointment"
        conn.commit()
        conn.close()

def insert_record(db_file, record):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''INSERT INTO records (title, date, category, summary, appointment)
                 VALUES (?, ?, ?, ?, ?)''', (record['Title'], record['Date'], record['Category'], record['Summary'], record['Appointment']))
    conn.commit()
    conn.close()

def record_exists(db_file, title):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''SELECT * FROM records WHERE title = ?''', (title,))
    result = c.fetchone()
    conn.close()
    return result is not None

def scrape_professionearchitetto(db_file):
    base_url = "https://www.professionearchitetto.it/key/concorsi-di-progettazione/"
    results = []

    # Funzione per estrarre il numero totale di pagine
    def extract_total_pages(soup):
        numeratore = soup.find('div', class_='numeratore')
        if numeratore:
            return len(numeratore.find_all('a')) + 1
        else:
            return 1

    # Funzione per estrarre i record da una pagina
    def extract_records_from_page(soup):
        articles = soup.find_all('article', class_='addlink')
        page_results = []

        for article in articles:
            title = article.find('h2', class_='entry-title').text.strip()
            date = article.find('time', class_='date').text.strip()
            category = article.find('span', class_='categoria').text.strip()
            summary = article.find('div', class_='entry-summary').text.strip()
            appointment = article.find('span', class_='appuntamento').text.strip()  # Aggiunge il campo "appuntamento"

            # Wrap text per ogni campo
            title = '\n'.join(textwrap.wrap(title, width=50))
            category = '\n'.join(textwrap.wrap(category, width=50))
            summary = '\n'.join(textwrap.wrap(summary, width=50))
            appointment = '\n'.join(textwrap.wrap(appointment, width=50))

            result = {
                'Title': title,
                'Date': datetime.strptime(date, '%d.%m.%Y').strftime('%Y-%m-%d'),  # Formato data standard
                'Category': category,
                'Summary': summary,
                'Appointment': appointment  # Aggiunge il campo "appuntamento"
            }
            page_results.append(result)

        return page_results

    # Loop attraverso tutte le pagine di risultati
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    total_pages = extract_total_pages(soup)

    for page in range(1, total_pages + 1):
        if page > 1:
            response = requests.get(base_url + str(page))
            soup = BeautifulSoup(response.text, 'html.parser')
        records = extract_records_from_page(soup)
        for record in records:
            if not record_exists(db_file, record['Title']):
                insert_record(db_file, record)
                results.append(record)

    return results

if __name__ == "__main__":
    db_file = "records.db"
    create_database(db_file)
    records = scrape_professionearchitetto(db_file)
    if records:
        headers = records[0].keys()
        rows = [record.values() for record in records]
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    else:
        print("Nessun nuovo concorso trovato.")

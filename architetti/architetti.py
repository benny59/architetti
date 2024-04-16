import os
import sqlite3
import requests
from bs4 import BeautifulSoup
import textwrap
from datetime import datetime
import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
import time

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Funzione per creare il database se non esiste
def create_database(db_file):
    if not os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS records
                     (id INTEGER PRIMARY KEY,
                     title TEXT,
                     date TEXT,
                     category TEXT,
                     summary TEXT)''')
        conn.commit()
        conn.close()

# Funzione per inserire un record nel database
def insert_record(db_file, record):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''INSERT INTO records (title, date, category, summary)
                 VALUES (?, ?, ?, ?)''', (record['Title'], record['Date'], record['Category'], record['Summary']))
    conn.commit()
    conn.close()

# Funzione per verificare se un record esiste già nel database
def record_exists(db_file, title):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''SELECT * FROM records WHERE title = ?''', (title,))
    result = c.fetchone()
    conn.close()
    return result is not None

# Funzione per lo scraping del sito web e l'estrazione dei record
# Funzione per lo scraping del sito web e l'estrazione dei record
# Funzione per lo scraping del sito web e l'estrazione dei record
def scrape_professionearchitetto(db_file):
    logging.info('Inizio lo scraping...')
    base_url = "https://www.professionearchitetto.it/key/concorsi-di-progettazione/"
    results = []

    # Funzione per estrarre i record da una pagina
    def extract_records_from_page(soup):
        articles = soup.find_all('article', class_='addlink')
        page_results = []

        for article in articles:
            title = article.find('h2', class_='entry-title').text.strip()
            date = article.find('time', class_='date').text.strip()
            category = article.find('span', class_='categoria').text.strip()
            
            # Gestisci l'attributo 'data-src' se presente, altrimenti usa 'src'
            img_tag = article.find('img')
            if img_tag and 'data-src' in img_tag.attrs:
                image = img_tag['data-src']
            elif img_tag and 'src' in img_tag.attrs:
                image = img_tag['src']
            else:
                image = None
            
            summary = article.find('div', class_='entry-summary').text.strip()

            # Wrap text
            title = '\n'.join(textwrap.wrap(title, width=50))
            category = '\n'.join(textwrap.wrap(category, width=50))
            summary = '\n'.join(textwrap.wrap(summary, width=50))

            result = {
                'Title': title,
                'Date': datetime.strptime(date, '%d.%m.%Y').strftime('%Y-%m-%d'),  # Formato data standard
                'Category': category,
                'Image': image,
                'Summary': summary
            }
            page_results.append(result)

        return page_results

    # Esegui lo scraping fino a quando ci sono record sulla pagina o si raggiunge il limite massimo di pagine
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
            if not record_exists(db_file, record['Title']):
                insert_record(db_file, record)
                results.append(record)
        
        page_num += 1

    logging.info('Scraping completato.')
    return results

# Funzione per l'invio di un messaggio Telegram
async def send_telegram_message(bot, chat_id, records):  # Aggiungi 'bot' come argomento
    #   bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])

    for record in records:
        # Formatta il record per renderlo più leggibile
        formatted_record = f"<b>Titolo:</b> <code style='color:blue'>{record['Title']}</code>\n" \
                        f"<b>Data:</b> <code style='color:green'>{record['Date']}</code>\n" \
                        f"<b>Categoria:</b> <code style='color:red'>{record['Category']}</code>\n" \
                        f"<b>Riassunto:</b> <i>{record['Summary']}</i>\n\n"

        # Invia il record formattato
        await bot.send_message(chat_id=chat_id, text=formatted_record, parse_mode=types.ParseMode.HTML)
        # Aggiungi un ritardo di 2 secondi tra l'invio di ciascun messaggio
        time.sleep(4)

# Funzione principale
async def main(bot):  # Passa l'oggetto bot come argomento
    db_file = "records.db"
    create_database(db_file)
    while True:
        logging.info('Avvio ciclo di scraping...')
        new_records = scrape_professionearchitetto(db_file)
        if new_records:
            logging.info('Nuovi record trovati.')
            chat_id = -1001993911752  # Sostituire con il vero chat_id del gruppo
            await send_telegram_message(bot, chat_id, new_records)  # Correggi la chiamata
        else:
            logging.info('Nessun nuovo record trovato.')
        # Aspetta 1 ora prima di eseguire un altro ciclo di scraping
        logging.info('Attendo 1 ora prima di eseguire un altro ciclo di scraping...')
        await asyncio.sleep(60)


# Esegui il loop principale
if __name__ == "__main__":
        bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
        asyncio.run(main(bot))  # Passa l'oggetto bot come argomento a main()


# Esegui il loop principale
if __name__ == "__main__":
        bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
        asyncio.run(main(bot))  # Passa l'oggetto bot come argomento a main()

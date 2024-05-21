import os
import sys
import time
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from hashlib import md5

# Aggiungi il percorso della directory corrente per l'importazione dei moduli locali
sys.path.append(os.path.dirname(__file__))

from scrape_professione_architetto import scrape_professione_architetto
from scrape_dummy_site import scrape_dummy_site
from scrape_europaconcorsi import scrape_site as scrape_europaconcorsi
from scrape_genovaconcorsi import scrape_genova_concorsi
from scrape_demanio import scrape_demanio
from scrape_aria import scrape_aria  # Importazione del nuovo file di scraping

# Configurazione del logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def main_wrapper():
    bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
    await main(bot)

async def main(bot):
    db_file = "records.db"
    sites = {
        'scrape_genova_concorsi': {
            'nickname': 'genovaconcorsi',
            'scrape_function': scrape_genova_concorsi,
            'url': 'https://appalti.comune.genova.it/PortaleAppalti/it/homepage.wp?actionPath=/ExtStr2/do/FrontEnd/Bandi/view.action',
            'run': True  # Esegui solo quando è True
        },
        'scrape_europaconcorsi': {
            'nickname': 'europaconcorsi',
            'scrape_function': scrape_europaconcorsi,
            'url': 'https://europaconcorsi.com/bandi/partecipazione-ristretta',
            'run': True  # Esegui solo quando è True
        },
        'professione_architetto': {
            'nickname': 'professione_architetto',
            'scrape_function': scrape_professione_architetto,
            'url': 'https://www.professionearchitetto.it/key/concorsi-di-progettazione/',
            'run': True  # Esegui solo quando è True
        },
        'dummy_site': {
            'nickname': 'dummy_site',
            'scrape_function': scrape_dummy_site,
            'url': 'http://example.com/dummy-site-url',
            'run': False  # Esegui solo quando è True
        },
        'scrape_demanio': {
            'nickname': 'demanio',
            'scrape_function': scrape_demanio,
            'url': 'https://www.agenziademanio.it/it/gare-aste/lavori/?garaFilters=r%3A07',
            'run': True  # Esegui solo quando è True
        },
        'scrape_aria': {  # Aggiungi il nuovo sito qui
            'nickname': 'aria',
            'scrape_function': scrape_aria,
            'url': 'https://www.sintel.regione.lombardia.it/eprocdata/sintelSearch.xhtml',
            'run': True  # Esegui solo quando è True
        }
    }

    create_database(db_file, sites)

    while True:
        logging.info('Starting scraping cycle...')
        for site_name, site_info in sites.items():
            if site_info['run']:
                new_records = site_info['scrape_function'](db_file, site_info['url'])
                if new_records:
                    logging.info(f'New records found for {site_name}.')
                    chat_id = -1001993911752  # Group chat ID, puoi cambiarlo con il chat ID desiderato
                    await send_telegram_message(bot, chat_id, new_records)
                else:
                    logging.info(f'No new records found for {site_name}.')

        logging.info('Waiting 1 hour before running another scraping cycle...')
        await asyncio.sleep(3600)

def create_database(db_file, sites):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    for site_name, site_info in sites.items():
        table_name = f"records_{site_info['nickname']}"
        c.execute(f'''CREATE TABLE IF NOT EXISTS {table_name}
                     (id INTEGER PRIMARY KEY,
                      title TEXT,
                      date TEXT,
                      category TEXT,
                      summary TEXT,
                      url TEXT,
                      checksum TEXT)''')
        c.execute(f'''CREATE INDEX IF NOT EXISTS idx_checksum_{site_info['nickname']}
                      ON {table_name} (checksum)''')
    conn.commit()
    conn.close()

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

async def send_telegram_message(bot, chat_id, records):
    for record in records:
        try:
            # Ensure all required keys are present
            required_keys = ['title', 'date', 'category', 'summary', 'url', 'checksum']
            for key in required_keys:
                if key not in record:
                    raise KeyError(f"Missing key: {key}")
        except KeyError as e:
            logging.error(f"Record missing required key: {e}")
            # Log the incomplete record for debugging purposes
            logging.error(f"Incomplete record: {record}")
            continue  # Skip this record and proceed with the next one
        
        title = record.get('title', 'No Title')
        date = record.get('date', 'No Date Provided')
        category = record.get('category', 'No Category')
        summary = record.get('summary', 'No Summary')
        url = record.get('url', None)

        message = (f"<b>Titolo:</b> <code style='color:blue'>{title}</code>\n"
                   f"<b>Data:</b> <code style='color:green'>{date}</code>\n"
                   f"<b>Categoria:</b> <code style='color:red'>{category}</code>\n"
                   f"<b>Riassunto:</b> <i>{summary}</i>\n")
        if url:
            message += f"<a href='{url}'>Link al concorso</a>\n"

        #await bot.send_message(chat_id=chat_id, text=message, parse_mode=types.ParseMode.HTML)
        #await asyncio.sleep(4)

if __name__ == "__main__":
    asyncio.run(main_wrapper())

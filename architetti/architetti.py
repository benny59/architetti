import os
import asyncio
from aiogram import Bot, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import logging
import sqlite3
import sys
sys.path.append(os.path.dirname(__file__))  # Assicurati che questa riga sia all'inizio del file
from aiogram import Bot
from scrape_professione_architetto import scrape_professione_architetto
from scrape_dummy_site import scrape_dummy_site


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main_wrapper():
    bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
    await main(bot)

async def main(bot):
    db_file = "records.db"
    sites = {
        'professione_architetto': {
            'nickname': 'professione_architetto',
            'scrape_function': scrape_professione_architetto
        },
        'dummy_site': {
            'nickname': 'dummy_site',
            'scrape_function': scrape_dummy_site
        }
        # Aggiungi altri siti qui...
    }

    create_database(db_file, sites)

    while True:
        logging.info('Starting scraping cycle...')

        for site_name, site_info in sites.items():
            new_records = site_info['scrape_function'](db_file)

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
              (record['Title'], record['Date'], record['Category'], record['Summary'], record['URL'], record['Checksum']))
    conn.commit()
    conn.close()

def record_exists(db_file, table_name, checksum):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(f'''SELECT * FROM {table_name} WHERE checksum = ?''', (checksum,))
    result = c.fetchone()
    conn.close()
    if result:
        logging.debug(f"Record with checksum {checksum} already exists.")
    else:
        logging.debug(f"Record with checksum {checksum} does not exist.")
    return result is not None
    
import time
from aiogram import types

async def send_telegram_message(bot, chat_id, records):
    for record in records:
        # Estrai le informazioni dal record
        title = record['Title']
        date = record['Date']
        category = record['Category']
        summary = record['Summary']
        url = record['URL'] if 'URL' in record else None  # Estrai l'URL se presente

        # Costruisci il messaggio
        message = f"<b>Titolo:</b> <code style='color:blue'>{title}</code>\n" \
                  f"<b>Data:</b> <code style='color:green'>{date}</code>\n" \
                  f"<b>Categoria:</b> <code style='color:red'>{category}</code>\n" \
                  f"<b>Riassunto:</b> <i>{summary}</i>\n"
        if url:
            message = f"<a href='{url}'>Link al concorso</a>\n"

        # Invia il messaggio
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=types.ParseMode.HTML)
        # Aggiungi un ritardo di 4 secondi tra l'invio di ciascun messaggio
        time.sleep(4)

if __name__ == "__main__":
    asyncio.run(main_wrapper())

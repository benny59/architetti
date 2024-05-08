import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib

def scrape_dummy_site(db_file,notused):
    from architetti import record_exists, insert_record  # Importazione locale per evitare circular import
    results = []
    dummy_records = [
        {
            'Title': 'Titolo 1',
            'Date': '2024-01-01',
            'Category': 'Categoria 1',
            'Summary': 'Riassunto 1',
            'URL': None,
            'Checksum': '1'
        },
        {
            'Title': 'Titolo 2',
            'Date': '2024-01-02',
            'Category': 'Categoria 2',
            'Summary': 'Riassunto 2',
            'URL': None,
            'Checksum': '2'
        },
        {
            'Title': 'Titolo 3',
            'Date': '2024-01-03',
            'Category': 'Categoria 3',
            'Summary': 'Riassunto 3',
            'URL': None,
            'Checksum': '3'
        }
    ]
    for record in dummy_records:
        if not record_exists(db_file, 'records_dummy_site', record['Checksum']):
            insert_record(db_file, 'records_dummy_site', record)
            results.append(record)

    return results

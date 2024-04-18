require 'sqlite3'
require 'telegram/bot'
require 'nokogiri'
require 'open-uri'
require 'logger'

# Configurazione del logger
def setup_logger
  logger = Logger.new(STDOUT)
  logger.level = Logger::INFO
  logger
end

LOGGER = setup_logger

# Funzione per creare il database se non esiste
def create_database(db_file)
  SQLite3::Database.new(db_file) unless File.exist?(db_file)
  db = SQLite3::Database.open(db_file)
  db.execute('CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, title TEXT, date TEXT, category TEXT, summary TEXT)')
  db.close
end

# Funzione per inserire un record nel database
def insert_record(db_file, record)
  db = SQLite3::Database.open(db_file)
  db.execute('INSERT INTO records (title, date, category, summary) VALUES (?, ?, ?, ?)', [record['Title'], record['Date'], record['Category'], record['Summary']])
  db.close
end

# Funzione per verificare se un record esiste già nel database
def record_exists(db_file, title)
  db = SQLite3::Database.open(db_file)
  result = db.execute('SELECT * FROM records WHERE title = ?', [title])
  db.close
  !result.empty?
end

# Funzione per lo scraping del sito web e l'estrazione dei record
def scrape_professionearchitetto(db_file)
  LOGGER.info('Inizio lo scraping...')
  base_url = "https://www.professionearchitetto.it/key/concorsi-di-progettazione/"
  results = []

  # Funzione per estrarre i record da una pagina
  def extract_records_from_page(url)
    page = Nokogiri::HTML(URI.open(url))
    articles = page.css('article.addlink')
    page_results = []

    articles.each do |article|
      title = article.css('h2.entry-title').text.strip
      date = article.css('time.date').text.strip
      category = article.css('span.categoria').text.strip
      image = article.css('img').first['data-src'] || article.css('img').first['src']
      summary = article.css('div.entry-summary').text.strip

      # Wrap text
      title = title.scan(/.{1,50}/).join("\n")
      category = category.scan(/.{1,50}/).join("\n")
      summary = summary.scan(/.{1,50}/).join("\n")

      result = {
        'Title': title,
        'Date': DateTime.strptime(date, '%d.%m.%Y').strftime('%Y-%m-%d'),  # Formato data standard
        'Category': category,
        'Image': image,
        'Summary': summary
      }
      page_results.append(result)
    end

    page_results
  end

  # Esegui lo scraping fino a quando ci sono record sulla pagina o si raggiunge il limite massimo di pagine
  max_pages = 10
  page_num = 1
  while page_num <= max_pages
    url = "#{base_url}?pag=#{page_num}"
    records = extract_records_from_page(url)

    break if records.empty?

    records.each do |record|
      unless record_exists(db_file, record[:'Title'])
        insert_record(db_file, record)
        results.append(record)
      end
    end

    page_num += 1
  end

  LOGGER.info('Scraping completato.')
  results
end

# Funzione per l'invio di un messaggio Telegram
def send_telegram_message(bot, chat_id, records)
  records.each do |record|
    formatted_record = "<b>Titolo:</b> #{record[:'Title']}\n" \
                       "<b>Data:</b> #{record[:'Date']}\n" \
                       "<b>Categoria:</b> #{record[:'Category']}\n" \
                       "<b>Riassunto:</b> #{record[:'Summary']}\n\n"

    bot.api.send_message(chat_id: chat_id, text: formatted_record, parse_mode: 'HTML')
    sleep(2) # Aggiungi un ritardo di 2 secondi tra l'invio di ciascun messaggio
  end
end

# Funzione principale
def main
  db_file = "records.db"
  create_database(db_file)

  Telegram::Bot::Client.run(ENV['TELEGRAM_BOT_TOKEN']) do |bot|
    LOGGER.info('Avvio ciclo di scraping...')
    new_records = scrape_professionearchitetto(db_file)
    if new_records.any?
      LOGGER.info('Nuovi record trovati.')
      chat_id = -1001993911752  # Sostituire con il vero chat_id del gruppo
      send_telegram_message(bot, chat_id, new_records)
    else
      LOGGER.info('Nessun nuovo record trovato.')
    end

    LOGGER.info('Attendo 1 ora prima di eseguire un altro ciclo di scraping...')
    sleep(3600) # Aspetta 1 ora prima di eseguire un altro ciclo di scraping
  end
end

# Esegui il programma
main if __FILE__ == $PROGRAM_NAME

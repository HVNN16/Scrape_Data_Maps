import os

# Định nghĩa đường dẫn thư mục
BASE_DIR = "scrape_data"
FILES = {
    "README.md": """# Web Scraping Project

This project is designed to scrape data from a website and store it in a database.

## Project Structure
- `requirements.txt`: List of Python dependencies.
- `config.py`: Configuration settings (e.g., URLs, API keys).
- `db.py`: Database connection and storage logic.
- `progress.py`: Progress tracking utilities.
- `geocode.py`: Geocoding utilities for location-based data.
- `scroll.py`: Handles infinite scrolling for dynamic websites.
- `parser.py`: Parses raw scraped data.
- `scraper.py`: Main script to run the scraper.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Configure settings in `config.py`.
3. Run the scraper: `python scraper.py`
""",
    "requirements.txt": """requests==2.31.0
beautifulsoup4==4.12.2
selenium==4.15.2
tqdm==4.66.1
pandas==2.2.2
sqlite3
""",
    "config.py": """# Configuration settings for the scraper
BASE_URL = "https://example.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"
}
DATABASE_PATH = "scraped_data.db"
""",
    "db.py": """import sqlite3

def init_db():
    conn = sqlite3.connect('scraped_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''') 
    conn.commit()
    conn.close()

def save_data(title, url):
    conn = sqlite3.connect('scraped_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO data (title, url) VALUES (?, ?)', (title, url))
    conn.commit()
    conn.close()
""",
    "progress.py": """from tqdm import tqdm

def track_progress(iterable, desc="Processing"):
    return tqdm(iterable, desc=desc)
""",
    "geocode.py": """# Placeholder for geocoding functionality
def geocode_address(address):
    # Implement geocoding logic (e.g., using Google Maps API or Nominatim)
    pass
""",
    "scroll.py": """from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scroll_page(driver):
    # Implement scrolling logic for dynamic websites
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    WebDriverWait(driver, 10).until(
 acuity>        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
""",
    "parser.py": """from bs4 import BeautifulSoup

def parse_page(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # Example: Extract all article titles and URLs
    items = []
    for article in soup.select('article'):
        title = article.select_one('h2').text.strip() if article.select_one('h2') else ''
        url = article.select_one('a')['href'] if article.select_one('a') else ''
        items.append({'title': title, 'url': url})
    return items
""",
    "scraper.py": """import requests
from bs4 import BeautifulSoup
from config import BASE_URL, HEADERS
from db import init_db, save_data
from parser import parse_page
from progress import track_progress

def scrape():
    init_db()
    response = requests.get(BASE_URL, headers=HEADERS)
    if response.status_code == 200:
        items = parse_page(response.text)
        for item in track_progress(items, desc="Saving data"):
            save_data(item['title'], item['url'])
        print(f"Scraped and saved {len(items)} items.")
    else:
        print(f"Failed to fetch page: {response.status_code}")

if __name__ == "__main__":
    scrape()
"""
}

# Tạo thư mục và file
os.makedirs(BASE_DIR, exist_ok=True)

for filename, content in FILES.items():
    file_path = os.path.join(BASE_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created {file_path}")

print(f"Directory structure created at {BASE_DIR}/")
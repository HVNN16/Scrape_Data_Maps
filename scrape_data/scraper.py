# scraper.py
# File chạy chính. Tích hợp: config + db + progress + geocode + scroll + parser

import time
import random
from datetime import datetime
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    PROVINCE_DISTRICTS, KEYWORDS,
    SELENIUM_HEADLESS, SELENIUM_USER_AGENT
)
from db import connect_postgres, ensure_tables, save_store
from progress import progress_get, progress_upsert
from geocode import reverse_geocode
from scroll import scroll_to_list_bottom
from parser import parse_business_card

def build_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--disable-gpu')
    options.add_argument(f'user-agent={SELENIUM_USER_AGENT}')
    if SELENIUM_HEADLESS:
        options.add_argument('--headless=new')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def main():
    total_new = 0
    total_dup = 0

    pg_conn, pg_cur = connect_postgres()
    ensure_tables(pg_cur, pg_conn)

    driver = build_driver()

    try:
        for province, districts in PROVINCE_DISTRICTS.items():
            for district in districts:
                for keyword in KEYWORDS:

                    # Resume tiến trình
                    pg = progress_get(pg_cur, province, district, keyword)
                    if pg and pg['status'] == 'done':
                        print(f"[SKIP] Done rồi: {keyword} @ {district}, {province}")
                        continue
                    progress_upsert(pg_cur, pg_conn, province, district, keyword, status='running')

                    print(f"===== Tìm: {keyword} tại {district}, {province} =====")
                    search_query = f"{keyword} tại {district} {province}"
                    url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}/"
                    driver.get(url)
                    time.sleep(random.uniform(5, 8))

                    # phát hiện captcha
                    ps = driver.page_source.lower()
                    if ("captcha" in ps) or ("detected unusual traffic" in ps):
                        print(f"[STOP] CAPTCHA @ {district}, {province} -> partial")
                        progress_upsert(pg_cur, pg_conn, province, district, keyword, status='partial')
                        continue

                    # feed
                    try:
                        feed = WebDriverWait(driver, 12).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                        )
                    except Exception as e:
                        print(f"[DEBUG] Không thấy feed @ {district}, {province}: {e}")
                        progress_upsert(pg_cur, pg_conn, province, district, keyword, status='failed')
                        continue

                    # cuộn đến đáy
                    scroll_to_list_bottom(driver, feed)

                    # parse
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    cards = soup.find_all('div', class_=lambda x: x and 'Nv2PK' in x)
                    total_cards = len(cards)
                    print(f"[DEBUG] Tổng {total_cards} kết quả @ {district}, {province}")

                    saved_here = 0
                    seen = 0
                    for div in cards:
                        seen += 1
                        try:
                            info = parse_business_card(div)

                            # Log trước khi geocode (để thấy tiến trình trong lúc chờ OSM)
                            short_name = (info["name"][:60] + '...') if len(info["name"]) > 60 else info["name"]
                            print(f"[{seen:03d}/{total_cards}] Đang xử lý: {short_name} | Cat={info['category']}")

                            # reverse geocode (địa chỉ)
                            addr = reverse_geocode(info["lat"], info["lng"])

                            store_data = {
                                'province': province,
                                'district': district,
                                'place_id': info["place_id"],
                                'name': info["name"],
                                'image': info["image"],
                                'rating': info["rating"],
                                'category': info["category"],
                                'status': info["status"],
                                'closing_time': info["closing_time"],
                                'phone': info["phone"],
                                'latitude': float(info["lat"]) if info["lat"] not in (None, 'N/A', '') else None,
                                'longitude': float(info["lng"]) if info["lng"] not in (None, 'N/A', '') else None,
                                'address': addr,
                                'map_url': info["map_url"],
                                'created_at': datetime.now()
                            }

                            if save_store(pg_cur, pg_conn, store_data):
                                total_new += 1
                                saved_here += 1
                                addr_short = (addr[:70] + '...') if addr and len(addr) > 70 else (addr or 'None')
                                print(f"   → [SAVED] {short_name} | Rating={info['rating']} | Phone={info['phone']} | Addr={addr_short}")
                            else:
                                total_dup += 1
                                print(f"   → [DUP]   {short_name}")

                        except Exception as e:
                            print(f"   → [ERROR] {short_name} :: {e}")

                    print(f"[INFO] Lưu mới {saved_here}/{total_cards} mục @ {district}, {province}")
                    progress_upsert(pg_cur, pg_conn, province, district, keyword, status='done')

                    time.sleep(random.uniform(5, 10))

    except KeyboardInterrupt:
        print("\n[EXIT] Ctrl+C — sẽ resume ở lần chạy sau (đánh dấu partial).")
    finally:
        # Tổng kết
        try:
            pg_cur.execute("SELECT COUNT(*) FROM grocery_stores;")
            total_in_db = pg_cur.fetchone()[0]
        except Exception:
            total_in_db = 'N/A'

        print("\n===== KẾT QUẢ =====")
        print(f"Insert mới: {total_new}")
        print(f"Bỏ trùng  : {total_dup}")
        print(f"Tổng trong DB: {total_in_db}")

        driver.quit()
        pg_cur.close()
        pg_conn.close()

if __name__ == "__main__":
    main()

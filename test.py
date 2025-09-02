# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras
import time
import random
import re
from datetime import datetime
import requests

# ================== CẤU HÌNH POSTGRES ==================
PG_DSN = "host=localhost port=5432 dbname=gisdb user=postgres password=12345"

def connect_postgres():
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    return conn, cur

def ensure_table(cur, conn):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS grocery_stores (
            id SERIAL PRIMARY KEY,
            province TEXT,
            district TEXT,
            place_id TEXT UNIQUE,
            name TEXT,
            image TEXT,
            rating TEXT,
            category TEXT,
            status TEXT,
            closing_time TEXT,
            phone TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            address TEXT,
            map_url TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("ALTER TABLE grocery_stores ADD COLUMN IF NOT EXISTS address TEXT;")
    cur.execute("ALTER TABLE grocery_stores ADD COLUMN IF NOT EXISTS map_url TEXT;")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_province ON grocery_stores (province);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_district ON grocery_stores (district);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_latlng ON grocery_stores (latitude, longitude);")
    conn.commit()

# ================== DANH SÁCH TỈNH/HUYỆN (demo) ==================
province_districts = {
    "Đà Nẵng": [
        "Quận Hải Châu"
    ],
}

# ================== TỪ KHÓA ==================
keywords = ["nhà thuốc", "cửa hàng vật tư nông nghiệp"]

# ================== SELENIUM ==================
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
# options.add_argument('--headless')  # bật khi chạy server
options.add_argument('--disable-gpu')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

total_saved = 0
total_duplicates = 0

# ================== TRÙNG LẶP ==================
def is_duplicate(cur, place_id):
    if not place_id or place_id == 'N/A':
        return None
    cur.execute("SELECT * FROM grocery_stores WHERE place_id = %s;", (place_id,))
    return cur.fetchone()

# ================== CATEGORY ==================
def get_category_from_name(name: str) -> str:
    """
    Chỉ 'Nhà thuốc' | 'Cửa hàng vật tư nông nghiệp' | 'Khác'
    """
    n = (name or "").lower()
    if any(k in n for k in ['nhà thuốc', 'pharmacy', 'quầy thuốc', 'pharmacity', 'hiệu thuốc']):
        return 'Nhà thuốc'
    if any(k in n for k in ['vật tư nông nghiệp', 'cửa hàng vật tư', 'nông dược']):
        return 'Cửa hàng vật tư nông nghiệp'
    return 'Khác'

# ================== REVERSE GEOCODING (Nominatim) ==================
_geocode_cache = {}

def reverse_geocode(lat, lng):
    """
    Trả về display_name từ lat/lng bằng Nominatim (OSM).
    Tôn trọng rate limit (~1 req/s) và set User-Agent rõ ràng.
    """
    try:
        if lat in (None, 'N/A', '') or lng in (None, 'N/A', ''):
            return None
        latf = float(lat); lngf = float(lng)
        key = (round(latf, 6), round(lngf, 6))
        if key in _geocode_cache:
            return _geocode_cache[key]

        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"lat": key[0], "lon": key[1], "format": "jsonv2", "addressdetails": 1}
        headers = {"User-Agent": "poi-coverage-scraper/1.0 (contact: your_email@example.com)"}
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("display_name")
            _geocode_cache[key] = addr
            time.sleep(1.1)  # tôn trọng rate limit
            return addr
        return None
    except Exception:
        return None

# ================== CUỘN DANH SÁCH HIỆU QUẢ ==================
def _count_cards(driver):
    # Các card kết quả trong list thường có class Nv2PK
    return len(driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK"))

def scroll_to_list_bottom(driver, feed_elem, patience=4, max_rounds=120):
    """
    Cuộn đến đáy danh sách:
    - Dùng JS: scrollTop = scrollHeight (ổn định hơn gửi END)
    - Dừng khi không tăng số item trong 'patience' vòng liên tiếp
    - 'max_rounds' để tránh vòng lặp vô hạn
    """
    # Chờ ít nhất 1 item xuất hiện
    WebDriverWait(driver, 15).until(lambda d: _count_cards(d) > 0)

    prev = -1
    same = 0
    rounds = 0

    while rounds < max_rounds:
        rounds += 1
        # Cuộn tới đáy hiện tại
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed_elem)

        # Chờ tối đa 3s nếu số item tăng
        try:
            WebDriverWait(driver, 3).until(lambda d: _count_cards(d) > prev)
            curr = _count_cards(driver)
        except TimeoutException:
            curr = _count_cards(driver)

        # Debug tuỳ thích
        # print(f"[SCROLL] round {rounds} -> {curr} items")

        if curr == prev:
            same += 1
        else:
            same = 0
            prev = curr

        if same >= patience:
            # Không thấy item mới trong 'patience' vòng => coi như đáy thật
            break

        # Nghỉ nhẹ cho Maps load
        time.sleep(random.uniform(0.8, 1.2))

# ================== LƯU POSTGRES ==================
def save_to_postgres(cur, conn, store_data):
    global total_saved, total_duplicates

    place_id = store_data.get('place_id')
    existing = is_duplicate(cur, place_id)
    if existing:
        total_duplicates += 1
        existing_name = existing['name'] if isinstance(existing, psycopg2.extras.DictRow) else existing[3]
        print(f"[DUPLICATE] {store_data.get('name', 'N/A')} (place_id={place_id}) ~ trùng: {existing_name}")
        return False

    try:
        cur.execute("""
            INSERT INTO grocery_stores (
                province, district, place_id, name, image, rating, category,
                status, closing_time, phone, latitude, longitude, address, map_url, created_at
            ) VALUES (
                %(province)s, %(district)s, %(place_id)s, %(name)s, %(image)s, %(rating)s, %(category)s,
                %(status)s, %(closing_time)s, %(phone)s, %(latitude)s, %(longitude)s, %(address)s, %(map_url)s, %(created_at)s
            )
            ON CONFLICT (place_id) DO NOTHING;
        """, store_data)
        conn.commit()

        if cur.rowcount == 0:
            total_duplicates += 1
            print(f"[DUPLICATE] Bỏ qua (ON CONFLICT): {store_data.get('name','N/A')} (place_id={place_id})")
            return False
        else:
            total_saved += 1
            print(f"[SAVED] {store_data.get('name','N/A')}")
            return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Lỗi khi lưu PostgreSQL: {e}")
        return False

# ================== BACKFILL (tùy chọn) ==================
def backfill_addresses(cur, conn, limit=500):
    cur.execute("""
        SELECT id, latitude, longitude FROM grocery_stores
        WHERE (address IS NULL OR address = '' )
          AND latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT %s;
    """, (limit,))
    rows = cur.fetchall()

    updated = 0
    for r in rows:
        _id, lat, lng = r['id'], r['latitude'], r['longitude']
        addr = reverse_geocode(lat, lng)
        if addr:
            cur.execute("UPDATE grocery_stores SET address = %s WHERE id = %s;", (addr, _id))
            conn.commit()
            updated += 1
    print(f"[BACKFILL] Đã cập nhật {updated} địa chỉ.")

# ================== MAIN ==================
def main():
    global total_saved, total_duplicates

    pg_conn, pg_cur = connect_postgres()
    ensure_table(pg_cur, pg_conn)

    for province, districts in province_districts.items():
        for district in districts:
            for keyword in keywords:
                print(f"===== Đang tìm kiếm: {keyword} tại {district}, {province} =====")
                search_query = f"{keyword} tại {district} {province}"
                url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}/"
                driver.get(url)
                time.sleep(random.uniform(5, 8))

                # Phát hiện CAPTCHA (thô sơ)
                page_source_lower = driver.page_source.lower()
                if ("captcha" in page_source_lower) or ("detected unusual traffic" in page_source_lower):
                    print(f"[STOP] CAPTCHA tại {district}, {province}.")
                    break

                # Tìm container danh sách
                try:
                    scroll_container = WebDriverWait(driver, 12).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                    )
                except Exception as e:
                    print(f"[DEBUG] Không tìm thấy container danh sách tại {district}, {province}: {e}")
                    continue

                # Cuộn đến đáy danh sách (phiên bản bền)
                scroll_to_list_bottom(driver, scroll_container, patience=4, max_rounds=120)

                # Parse sau khi đã cuộn hết
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                businesses = soup.find_all('div', class_=lambda x: x and 'Nv2PK' in x)
                print(f"[DEBUG] Tổng cộng {len(businesses)} cửa hàng cuối cùng tại {district}, {province}")

                district_saved = 0
                for business in businesses:
                    try:
                        # Tên
                        name_tag = business.find('div', class_='qBF1Pd')
                        name = name_tag.text.strip() if name_tag else 'N/A'

                        category = get_category_from_name(name)

                        # Place ID + URL
                        place_id = 'N/A'
                        map_url = None
                        link_tag = business.find('a', class_='hfpxzc', href=True)
                        if link_tag and 'href' in link_tag.attrs:
                            map_url = link_tag['href']
                            href = link_tag['href']
                            m = re.search(r'!19s([^?]+)', href) or re.search(r'data=[^!]+!1s([^!]+)', href)
                            if m:
                                place_id = m.group(1)

                        # Ảnh
                        image_url = 'N/A'
                        img_tag = business.find('img')
                        if img_tag and img_tag.get('src'):
                            image_url = img_tag['src']

                        # Rating
                        rating_tag = business.find('span', class_='MW4etd')
                        rating = rating_tag.text.strip() if rating_tag else 'N/A'

                        # Tọa độ
                        lat, lng = None, None
                        if link_tag:
                            href = link_tag['href']
                            m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', href)
                            if m:
                                lat, lng = m.groups()
                            else:
                                m = re.search(r'/@(-?\d+\.\d+),(-?\d+\.\d+)', href)
                                if m:
                                    lat, lng = m.groups()

                        # Trạng thái + số điện thoại
                        status, closing_time, phone = 'N/A', 'N/A', 'N/A'
                        info_tags = business.find_all('div', class_='W4Efsd')
                        if len(info_tags) > 1:
                            details_tag = info_tags[1]
                            status_tag = details_tag.find('span', style=lambda v: v and 'rgba(25,134,57' in v)
                            status = status_tag.text.strip() if status_tag else 'N/A'
                            closing_time_tag = details_tag.find('span', style='font-weight: 400;')
                            closing_time = closing_time_tag.text.strip(' ⋅ ').strip() if closing_time_tag else 'N/A'
                            phone_tag = details_tag.find('span', class_='UsdlK')
                            phone = phone_tag.text.strip() if phone_tag else 'N/A'

                        # Địa chỉ (reverse geocode)
                        address = reverse_geocode(lat, lng)

                        store_data = {
                            'province': province,
                            'district': district,
                            'place_id': place_id,
                            'name': name,
                            'image': image_url,
                            'rating': rating,
                            'category': category,
                            'status': status,
                            'closing_time': closing_time,
                            'phone': phone,
                            'latitude': float(lat) if lat not in (None, 'N/A', '') else None,
                            'longitude': float(lng) if lng not in (None, 'N/A', '') else None,
                            'address': address,
                            'map_url': map_url,
                            'created_at': datetime.now()
                        }

                        shown_addr = store_data['address'][:80] + '...' if store_data['address'] and len(store_data['address']) > 80 else store_data['address']
                        print(f"[DEBUG] {name} | Cat={category} | Phone={phone} | Addr={shown_addr or 'None'} | URL={'yes' if map_url else 'no'}")

                        if save_to_postgres(pg_cur, pg_conn, store_data):
                            district_saved += 1

                    except Exception as e:
                        print(f"[DEBUG] Lỗi khi xử lý một mục tại {district}, {province}: {e}")

                print(f"[INFO] Đã lưu {district_saved} cửa hàng mới tại {district}, {province}")
                time.sleep(random.uniform(5, 10))

    # Tổng kết
    pg_cur.execute("SELECT COUNT(*) FROM grocery_stores;")
    total_in_db = pg_cur.fetchone()[0]
    print("\n===== KẾT QUẢ CUỐI CÙNG =====")
    print(f"Tổng số cửa hàng đã lưu: {total_saved}")
    print(f"Tổng số cửa hàng trùng lặp bỏ qua: {total_duplicates}")
    print(f"Tổng số bản ghi trong database: {total_in_db}")

    # backfill_addresses(pg_cur, pg_conn, limit=1000)  # tuỳ chọn

    driver.quit()
    pg_cur.close()
    pg_conn.close()

if __name__ == "__main__":
    main()

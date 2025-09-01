from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras
import time
import random
import re
from datetime import datetime

# ================== CẤU HÌNH POSTGRES ==================
# Điền DSN theo máy của bạn, ví dụ:
# "host=localhost port=5432 dbname=mydb user=myuser password=mypassword"
PG_DSN = "host=localhost port=5432 dbname=gisdb user=postgres password=12345"

def connect_postgres():
    conn = psycopg2.connect(PG_DSN)
    # DictCursor để lấy cột theo tên khi cần
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
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_province ON grocery_stores (province);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_district ON grocery_stores (district);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_latlng ON grocery_stores (latitude, longitude);")
    conn.commit()


# ================== DANH SÁCH TỈNH VÀ HUYỆN/QUẬN ==================
province_districts = {
    
    "Đà Nẵng": ["Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Liên Chiểu"],
   
}

# ================== DANH SÁCH TỪ KHÓA ==================
keywords = ["nhà thuốc", "cửa hàng tạp hóa"]

# ================== CẤU HÌNH SELENIUM ==================
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
# options.add_argument('--headless')  # Bật khi chạy server
options.add_argument('--disable-gpu')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

total_saved = 0
total_duplicates = 0

# ================== HÀM KIỂM TRA TRÙNG LẶP (Postgres) ==================
def is_duplicate(cur, place_id):
    """
    Kiểm tra trùng lặp dựa trên place_id. Trả về record nếu đã tồn tại.
    """
    if not place_id or place_id == 'N/A':
        return None
    cur.execute("SELECT * FROM grocery_stores WHERE place_id = %s;", (place_id,))
    return cur.fetchone()

# ================== HÀM PHÂN LOẠI CATEGORY ==================
def get_category_from_name(name):
    name = (name or "").lower()
    if 'tạp hoá' in name or 'tạp hóa' in name:
        return 'Tạp hóa'
    elif 'bách hoá' in name or 'bách hóa' in name:
        return 'Bách hóa'
    elif any(k in name for k in ['cửa hàng tiện lợi', 'siêu thị mini', 'minimart']):
        return 'Cửa hàng tiện lợi'
    elif 'nhà thuốc' in name or 'pharmacy' in name:
        return 'Nhà thuốc'
    else:
        return 'Khác'

# ================== HÀM LƯU VÀO POSTGRES ==================
def save_to_postgres(cur, conn, store_data):
    """
    Lưu dữ liệu vào PostgreSQL nếu không trùng lặp (dựa theo place_id).
    Dùng ON CONFLICT(place_id) DO NOTHING để bỏ qua trùng.
    """
    global total_saved, total_duplicates

    place_id = store_data.get('place_id')
    existing = is_duplicate(cur, place_id)
    if existing:
        total_duplicates += 1
        print(f"[DUPLICATE] Cửa hàng mới: {store_data.get('name', 'N/A')} (place_id={place_id})")
        print(f"            Trùng với trong DB: {existing.get('name', 'N/A') if isinstance(existing, dict) else existing['name']} (place_id={place_id})\n")
        return False

    try:
        cur.execute("""
            INSERT INTO grocery_stores (
                province, district, place_id, name, image, rating, category,
                status, closing_time, phone, latitude, longitude, created_at
            ) VALUES (
                %(province)s, %(district)s, %(place_id)s, %(name)s, %(image)s, %(rating)s, %(category)s,
                %(status)s, %(closing_time)s, %(phone)s, %(latitude)s, %(longitude)s, %(created_at)s
            )
            ON CONFLICT (place_id) DO NOTHING;
        """, store_data)
        conn.commit()

        # Kiểm tra có chèn mới hay bị DO NOTHING (trùng)
        if cur.rowcount == 0:
            total_duplicates += 1
            print(f"[DUPLICATE] Bỏ qua (ON CONFLICT): {store_data.get('name', 'N/A')} (place_id={place_id})\n")
            return False
        else:
            total_saved += 1
            print(f"[SAVED] Đã lưu: {store_data.get('name', 'N/A')}")
            return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Lỗi khi lưu vào PostgreSQL: {e}")
        return False

# ================== MAIN ==================
def main():
    global total_saved, total_duplicates

    # Kết nối và chuẩn bị bảng
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

                # Phát hiện CAPTCHA (cực kỳ thô sơ)
                if "CAPTCHA" in driver.page_source or "detected unusual traffic" in driver.page_source.lower():
                    print(f"[STOP] Phát hiện CAPTCHA tại {district}, {province}. Dừng để tránh chặn IP.")
                    break

                # Tìm container danh sách
                try:
                    scroll_container = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
                except Exception as e:
                    print(f"[DEBUG] Không tìm thấy container danh sách tại {district}, {province}: {e}")
                    continue

                # Cuộn đến cuối
                last_count = 0
                same_count = 0
                while True:
                    scroll_container.send_keys(Keys.END)
                    time.sleep(random.uniform(2, 4))

                    temp_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    temp_businesses = temp_soup.find_all('div', class_=lambda x: x and 'Nv2PK' in x)
                    current_count = len(temp_businesses)
                    print(f"[DEBUG] Hiện có {current_count} cửa hàng...")

                    if current_count == last_count:
                        same_count += 1
                    else:
                        same_count = 0
                        last_count = current_count

                    if same_count >= 3:
                        print("[DEBUG] Đã cuộn hết kết quả.")
                        break

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                businesses = soup.find_all('div', class_=lambda x: x and 'Nv2PK' in x)
                print(f"[DEBUG] Tổng cộng {len(businesses)} cửa hàng cuối cùng tại {district}, {province}")

                district_saved = 0
                for business in businesses:
                    try:
                        # Tên
                        name_tag = business.find('div', class_='qBF1Pd')
                        name = name_tag.text if name_tag else 'N/A'

                        category = get_category_from_name(name)

                        # Place ID
                        place_id = 'N/A'
                        link_tag = business.find('a', class_='hfpxzc', href=True)
                        if link_tag and 'href' in link_tag.attrs:
                            href = link_tag['href']
                            match = re.search(r'!19s([^?]+)', href) or re.search(r'data=[^!]+!1s([^!]+)', href)
                            if match:
                                place_id = match.group(1)

                        # Ảnh
                        image_url = 'N/A'
                        img_tag = business.find('img')
                        if img_tag and img_tag.get('src'):
                            image_url = img_tag['src']

                        # Rating
                        rating_tag = business.find('span', class_='MW4etd')
                        rating = rating_tag.text if rating_tag else 'N/A'

                        # Tọa độ
                        lat, lng = 'N/A', 'N/A'
                        if link_tag:
                            href = link_tag['href']
                            match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', href)
                            if match:
                                lat, lng = match.groups()
                            else:
                                match = re.search(r'/@(-?\d+\.\d+),(-?\d+\.\d+)', href)
                                if match:
                                    lat, lng = match.groups()

                        # Trạng thái + số điện thoại
                        status, closing_time, phone = 'N/A', 'N/A', 'N/A'
                        info_tags = business.find_all('div', class_='W4Efsd')
                        if len(info_tags) > 1:
                            details_tag = info_tags[1]
                            status_tag = details_tag.find('span', style=lambda v: v and 'rgba(25,134,57' in v)
                            status = status_tag.text if status_tag else 'N/A'
                            closing_time_tag = details_tag.find('span', style='font-weight: 400;')
                            closing_time = closing_time_tag.text.strip(' ⋅ ') if closing_time_tag else 'N/A'
                            phone_tag = details_tag.find('span', class_='UsdlK')
                            phone = phone_tag.text if phone_tag else 'N/A'

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
                            'latitude': lat,
                            'longitude': lng,
                            'created_at': datetime.now()
                        }

                        print(f"[DEBUG] Trích xuất: {name} | PlaceID={place_id} | Cat={category} | Phone={phone}")

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

    # Đóng tài nguyên
    driver.quit()
    pg_cur.close()
    pg_conn.close()

if __name__ == "__main__":
    main()

# # scraper.py
# # File chạy chính. Tích hợp: config + db + progress + geocode + scroll + parser

# import time
# import random
# from datetime import datetime
# from bs4 import BeautifulSoup
# from selenium.webdriver.common.keys import Keys
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# from config import (
#     PROVINCE_DISTRICTS, KEYWORDS,
#     SELENIUM_HEADLESS, SELENIUM_USER_AGENT
# )
# from db import connect_postgres, ensure_tables, save_store
# from progress import progress_get, progress_upsert
# from geocode import reverse_geocode
# from scroll import scroll_to_list_bottom
# from parser import parse_business_card

# def build_driver():
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--disable-gpu')
#     options.add_argument(f'user-agent={SELENIUM_USER_AGENT}')
#     if SELENIUM_HEADLESS:
#         options.add_argument('--headless=new')
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
#     return driver

# def main():
#     total_new = 0
#     total_dup = 0

#     pg_conn, pg_cur = connect_postgres()
#     ensure_tables(pg_cur, pg_conn)

#     driver = build_driver()

#     try:
#         for province, districts in PROVINCE_DISTRICTS.items():
#             for district in districts:
#                 for keyword in KEYWORDS:

#                     # Resume tiến trình
#                     pg = progress_get(pg_cur, province, district, keyword)
#                     if pg and pg['status'] == 'done':
#                         print(f"[SKIP] Done rồi: {keyword} @ {district}, {province}")
#                         continue
#                     progress_upsert(pg_cur, pg_conn, province, district, keyword, status='running')

#                     print(f"===== Tìm: {keyword} tại {district}, {province} =====")
#                     # search_query = f"{keyword} tại {district} {province}"
#                     # url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}/"
#                     # driver.get(url)
#                     # time.sleep(random.uniform(5, 8))
#                     search_query = f"{keyword} tại {district} {province}"
#                     driver.get("https://www.google.com/maps/")

#                     try:
#                         # Chờ ô tìm kiếm xuất hiện
#                         search_box = WebDriverWait(driver, 15).until(
#                             EC.presence_of_element_located((By.ID, "searchboxinput"))
#                         )
#                         search_box.clear()
#                         search_box.send_keys(search_query)
#                         time.sleep(1)
#                         search_box.send_keys(Keys.ENTER)   # <-- Quan trọng: nhấn Enter
#                         print(f"[DEBUG] Đã nhập & nhấn Enter: {search_query}")
#                     except Exception as e:
#                         print(f"[ERROR] Không tìm thấy ô tìm kiếm: {e}")
#                         progress_upsert(pg_cur, pg_conn, province, district, keyword, status='failed')
#                         continue

#                     # Chờ kết quả load
#                     time.sleep(random.uniform(5, 8))

#                     # phát hiện captcha
#                     ps = driver.page_source.lower()
#                     if ("captcha" in ps) or ("detected unusual traffic" in ps):
#                         print(f"[STOP] CAPTCHA @ {district}, {province} -> partial")
#                         progress_upsert(pg_cur, pg_conn, province, district, keyword, status='partial')
#                         continue

#                     # feed
#                     try:
#                         feed = WebDriverWait(driver, 12).until(
#                             EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
#                         )
#                     except Exception as e:
#                         print(f"[DEBUG] Không thấy feed @ {district}, {province}: {e}")
#                         progress_upsert(pg_cur, pg_conn, province, district, keyword, status='failed')
#                         continue

#                     # cuộn đến đáy
#                     scroll_to_list_bottom(driver, feed)

#                     # parse
#                     soup = BeautifulSoup(driver.page_source, 'html.parser')
#                     cards = soup.find_all('div', class_=lambda x: x and 'Nv2PK' in x)
#                     total_cards = len(cards)
#                     print(f"[DEBUG] Tổng {total_cards} kết quả @ {district}, {province}")

#                     saved_here = 0
#                     seen = 0
#                     for div in cards:
#                         seen += 1
#                         try:
#                             info = parse_business_card(div)

#                             # Log trước khi geocode (để thấy tiến trình trong lúc chờ OSM)
#                             short_name = (info["name"][:60] + '...') if len(info["name"]) > 60 else info["name"]
#                             print(f"[{seen:03d}/{total_cards}] Đang xử lý: {short_name} | Cat={info['category']}")

#                             # reverse geocode (địa chỉ)
#                             addr = reverse_geocode(info["lat"], info["lng"])

#                             store_data = {
#                                 'province': province,
#                                 'district': district,
#                                 'place_id': info["place_id"],
#                                 'name': info["name"],
#                                 'image': info["image"],
#                                 'rating': info["rating"],
#                                 'category': info["category"],
#                                 'status': info["status"],
#                                 'closing_time': info["closing_time"],
#                                 'phone': info["phone"],
#                                 'latitude': float(info["lat"]) if info["lat"] not in (None, 'N/A', '') else None,
#                                 'longitude': float(info["lng"]) if info["lng"] not in (None, 'N/A', '') else None,
#                                 'address': addr,
#                                 'map_url': info["map_url"],
#                                 'created_at': datetime.now()
#                             }

#                             if save_store(pg_cur, pg_conn, store_data):
#                                 total_new += 1
#                                 saved_here += 1
#                                 addr_short = (addr[:70] + '...') if addr and len(addr) > 70 else (addr or 'None')
#                                 print(f"   → [SAVED] {short_name} | Rating={info['rating']} | Phone={info['phone']} | Addr={addr_short}")
#                             else:
#                                 total_dup += 1
#                                 print(f"   → [DUP]   {short_name}")

#                         except Exception as e:
#                             print(f"   → [ERROR] {short_name} :: {e}")

#                     print(f"[INFO] Lưu mới {saved_here}/{total_cards} mục @ {district}, {province}")
#                     progress_upsert(pg_cur, pg_conn, province, district, keyword, status='done')

#                     time.sleep(random.uniform(5, 10))

#     except KeyboardInterrupt:
#         print("\n[EXIT] Ctrl+C — sẽ resume ở lần chạy sau (đánh dấu partial).")
#     finally:
#         # Tổng kết
#         try:
#             pg_cur.execute("SELECT COUNT(*) FROM grocery_stores;")
#             total_in_db = pg_cur.fetchone()[0]
#         except Exception:
#             total_in_db = 'N/A'

#         print("\n===== KẾT QUẢ =====")
#         print(f"Insert mới: {total_new}")
#         print(f"Bỏ trùng  : {total_dup}")
#         print(f"Tổng trong DB: {total_in_db}")

#         driver.quit()
#         pg_cur.close()
#         pg_conn.close()

# if __name__ == "__main__":
#     main()

# scraper.py
# File chạy chính. Tích hợp: config + db + progress + geocode + scroll + parser
# ĐÃ BỔ SUNG bộ lọc địa bàn linh hoạt (quận/huyện/thị xã/thành phố & viết tắt)

import time
import random
import re
import unicodedata
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
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


# ========= Helpers lọc địa bàn (4 trường hợp, có quận/huyện/tx/tp và viết tắt) =========

_PFX_DIST = [
    "huyện", "quận", "thị xã", "thi xa", "thành phố", "thanh pho",
    "h.", "q.", "tx.", "tp.", "h", "q", "tx", "tp"
]
_PFX_PROV = ["tỉnh", "tinh", "thành phố", "thanh pho", "tp.", "tp"]

def _strip_accents(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def _norm(s: str) -> str:
    s = _strip_accents(s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)      # bỏ dấu câu
    s = re.sub(r"\s+", " ", s).strip()  # chuẩn hoá khoảng trắng
    return s

def _remove_leading_prefix(s: str, prefixes) -> str:
    """
    Bỏ các tiền tố hành chính đứng đầu, ví dụ:
    'huyện ba vì' -> 'ba vì', 'quận tây hồ' -> 'tây hồ', 'tp. ha noi' -> 'ha noi'
    """
    ns = _norm(s)
    for p in sorted(prefixes, key=len, reverse=True):
        p_norm = _norm(p)
        if ns.startswith(p_norm + " "):
            return ns[len(p_norm):].strip()
    return ns

def _mk_district_variants(district: str):
    """
    Sinh các biến thể cho district:
    - nguyên văn (chuẩn hoá): 'huyen ba vi', 'quan ba dinh', ...
    - chỉ tên trần: 'ba vi', 'ba dinh'
    - viết tắt có tiền tố: 'h ba vi', 'h. ba vi', 'q ba dinh', 'q. ba dinh', 'tx son tay', 'tp thu duc'
    """
    ns_full = _norm(district)
    bare = _remove_leading_prefix(district, _PFX_DIST)

    variants = set()
    variants.add(ns_full)
    variants.add(bare)

    # thêm dạng viết tắt/tiền tố rút gọn phổ biến
    for p in ["huyen", "h.", "h", "quan", "q.", "q", "thi xa", "tx.", "tx", "thanh pho", "tp.", "tp"]:
        variants.add(f"{p} {bare}")

    return {v.strip() for v in variants if v.strip()}

def _mk_province_variants(province: str):
    """
    Sinh các biến thể cho province:
    - nguyên văn: 'thanh pho ha noi', 'tinh bac ninh'...
    - rút gọn bỏ tiền tố: 'ha noi', 'bac ninh'
    - viết tắt phổ biến: 'tp ha noi', 'tp. ha noi'
    """
    ns_full = _norm(province)
    bare = _remove_leading_prefix(province, _PFX_PROV)

    variants = set()
    variants.add(ns_full)
    variants.add(bare)
    for p in ["thanh pho", "tp.", "tp", "tinh"]:
        variants.add(f"{p} {bare}")

    return {v.strip() for v in variants if v.strip()}

def in_target_area(addr: str, district: str, province: str) -> bool:
    """
    NHẸ TAY: Chỉ cần KHỚP MỘT trong hai:
      - addr chứa 1 biến thể của district (quận/huyện/thị xã/thành phố, viết tắt…)
      - HOẶC addr chứa 1 biến thể của province (tỉnh/thành phố, viết tắt…)

    Nghĩa là chỉ cần có 'Ba Vì' HOẶC có 'Hà Nội' (kể cả các biến thể như 'Q.', 'TP.', 'Thành phố'…)
    là pass bộ lọc.
    """
    if not addr:
        return False

    addr_norm = _norm(addr)
    dvars = _mk_district_variants(district)
    pvars = _mk_province_variants(province)

    has_d = any(v in addr_norm for v in dvars)
    has_p = any(v in addr_norm for v in pvars)

    # ĐIỂM KHÁC BIỆT: chỉ cần 1 trong 2 là True
    return has_d or has_p


# =============== Bộ lọc loại trừ “đông y/nam dược/cổ truyền/thú y” ===============

EXCLUDE_KEYWORDS = [
    "đông y", "nam dược", "cổ truyền", "y học cổ truyền",
    "thuốc bắc", "thú y", "thú y viện", "pet", "veterinary","thuốc nam", "dong y", "nam duoc", "co truyen", "y hoc co truyen",
    "thuoc bac", "thu y", "thu y vien", "thuy vien", "thuoc nam"
]

def _contains_any(text: str, terms) -> bool:
    """So khớp không dấu + lowercase để bắt cả 'dong y', 'thu y'..."""
    t = _norm(text or "")
    for k in terms:
        if _norm(k) in t:
            return True
    return False

def is_excluded_by_name_or_category(info: dict) -> bool:
    """
    Loại trừ nếu tên hoặc category có chứa từ khóa không mong muốn.
    - Dùng khi parser trả category từ hàm categorize(name) hoặc để trống.
    """
    name = info.get("name") or ""
    cat  = info.get("category") or ""
    blob = f"{name} {cat}"
    # Nếu parser đã phân loại "Loại trừ" thì cũng bỏ luôn
    if (cat.strip().lower() == "loại trừ"):
        return True
    return _contains_any(blob, EXCLUDE_KEYWORDS)


# ========= Selenium driver =========

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

                    print(f"===== Tìm: {keyword} {district}, {province} =====")
                    search_query = f"{keyword} {district} {province}"
                    driver.get("https://www.google.com/maps/")

                    try:
                        search_box = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.ID, "searchboxinput"))
                        )
                        search_box.clear()
                        search_box.send_keys(search_query)
                        time.sleep(1)
                        search_box.send_keys(Keys.ENTER)
                        print(f"[DEBUG] Đã nhập & nhấn Enter: {search_query}")
                    except Exception as e:
                        print(f"[ERROR] Không tìm thấy ô tìm kiếm: {e}")
                        progress_upsert(pg_cur, pg_conn, province, district, keyword, status='failed')
                        continue

                    # Chờ kết quả load
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
                        short_name = "N/A"
                        try:
                            info = parse_business_card(div)

                            # Log trước khi geocode
                            name_for_log = info.get("name") or "N/A"
                            short_name = (name_for_log[:60] + '...') if len(name_for_log) > 60 else name_for_log
                            print(f"[{seen:03d}/{total_cards}] Đang xử lý: {short_name} | Cat={info.get('category','')}")

                            # >>> Bộ lọc loại trừ đông y/nam dược/cổ truyền/thú y
                            if is_excluded_by_name_or_category(info):
                                print(f"   → [SKIP-EXCLUDE] {short_name} | Cat={info.get('category','')}")
                                continue

                            # Bắt buộc có toạ độ thật (từ !3d..!4d..)
                            if not info["lat"] or not info["lng"]:
                                print(f"   → [SKIP-NO-COORD] {short_name}")
                                continue

                            # Địa chỉ chi tiết
                            addr = reverse_geocode(info["lat"], info["lng"])

                            # Lọc địa bàn theo 4 trường hợp (và biến thể viết tắt/quận/tx/tp)
                            if not in_target_area(addr, district, province):
                                addr_short = (addr[:70] + '...') if addr and len(addr) > 70 else (addr or 'None')
                                print(f"   → [SKIP-OUT] {short_name} | Addr={addr_short} | NOT IN: {district}, {province}")
                                continue

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
                                'latitude': float(info["lat"]),
                                'longitude': float(info["lng"]),
                                'address': addr,
                                'map_url': info["map_url"],
                                'created_at': datetime.now()
                            }

                            if save_store(pg_cur, pg_conn, store_data):
                                saved_here += 1
                                print(f"   → [SAVED] {short_name}")
                            else:
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
        # Ở đây 'total_new' không tăng trực tiếp — bạn có thể cộng dồn trong save_store nếu muốn
        print(f"Tổng trong DB: {total_in_db}")

        driver.quit()
        pg_cur.close()
        pg_conn.close()

if __name__ == "__main__":
    main()


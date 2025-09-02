
# config.py
# Chứa hằng số, cấu hình hệ thống

# ====== Postgres ======
PG_DSN = "host=localhost port=5432 dbname=gisdb user=postgres password=12345"

# ====== Selenium ======
SELENIUM_HEADLESS = False          # True nếu chạy server
SELENIUM_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# ====== Crawl phạm vi demo ======
PROVINCE_DISTRICTS = {
    "Đà Nẵng": ["Quận Hải Châu"],
}

KEYWORDS = ["nhà thuốc", "cửa hàng vật tư nông nghiệp"]

# ====== Cuộn list ======
SCROLL_PATIENCE = 4
SCROLL_MAX_ROUNDS = 120
SCROLL_WAIT_ITEM = 15     # giây chờ có ít nhất 1 item đầu tiên
SCROLL_GAP_MINMAX = (0.8, 1.2)  # sleep ngẫu nhiên mỗi vòng cuộn

# ====== Reverse Geocoding (OSM/Nominatim) ======
OSM_USER_AGENT = "poi-coverage-scraper/1.0 (contact: your_email@example.com)"
OSM_RATE_LIMIT_SLEEP = 1.1   # giây

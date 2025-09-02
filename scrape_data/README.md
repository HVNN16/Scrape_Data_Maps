# Google Maps Scraper (PostgreSQL + Resume tiến trình)

## Cài đặt
pip install -r requirements.txt

## Cấu hình
- Sửa PG_DSN trong `config.py` cho đúng Postgres của bạn.
- Nếu chạy server: bật headless trong `config.py` (SELENIUM_HEADLESS=True)

## Chạy
python scraper.py

## Resume
- Tiến trình được lưu trong bảng `crawl_progress`. Lần sau chạy lại sẽ bỏ qua combo đã `done` và tiếp tục `pending`/`partial`.
- Muốn làm lại 1 combo:
  ```sql
  UPDATE crawl_progress
  SET status='pending'
  WHERE province='Đà Nẵng' AND district='Quận Hải Châu' AND keyword='nhà thuốc';


<!-- Tổng kết chức năng từng file

config.py: nơi đặt cấu hình (DSN Postgres, user-agent, headless, danh sách tỉnh/quận, keyword, tham số cuộn, cấu hình rate limit OSM).

db.py: kết nối DB, khởi tạo & migrate bảng dữ liệu (grocery_stores) và lưu bản ghi chống trùng.

progress.py: lưu/đọc tiến trình từng (tỉnh, huyện, keyword) để resume (trạng thái pending/running/partial/done/failed).

geocode.py: reverse geocoding từ lat/lng sang địa chỉ chi tiết bằng Nominatim (OSM) + cache + tôn trọng rate limit.

scroll.py: cuộn bền vững list Google Maps bằng scrollTop = scrollHeight, dừng khi không thấy item mới nhiều vòng liên tiếp.

parser.py: phân tích 1 card kết quả (name, rating, status, phone, place_id, map_url, lat/lng, image) và phân loại theo tên (Nhà thuốc / Cửa hàng vật tư nông nghiệp / Khác).

scraper.py: chương trình chính — khởi tạo Selenium, lặp các combo, cuộn → parse → geocode → lưu → cập nhật progress, và in tổng kết.

requirements.txt: các thư viện Python cần cài.

README.md: hướng dẫn cài đặt/chạy, cách resume và chỉnh sửa tiến trình. -->
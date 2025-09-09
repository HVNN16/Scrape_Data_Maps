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


# 🟢 Bước 1: Thu thập & Chuẩn hoá dữ liệu

## 📌 Giới thiệu
Ở bước 1, nhóm xây dựng công cụ **scraping Google Maps** bằng **Python + Selenium** để thu thập dữ liệu về:
- **Hiệu thuốc tây**  
- **Cửa hàng vật tư nông nghiệp**

Sau khi thu thập, dữ liệu được chuẩn hoá và lưu vào **PostgreSQL/PostGIS** để phục vụ cho các bước tiếp theo (loại bỏ trùng lặp, trực quan hoá, xây công cụ tìm kiếm khách hàng).

---

## 🗂️ Cấu trúc thư mục

scrape_data/
│── config.py # Cấu hình: danh sách tỉnh/huyện, keywords, user-agent
│── scraper.py # Script chính, điều khiển quá trình scraping
│── parser.py # Phân tích HTML của từng business card trong Google Maps
│── scroll.py # Tự động cuộn để tải đủ kết quả
│── geocode.py # Reverse geocoding: lấy địa chỉ từ tọa độ
│── db.py # Kết nối PostgreSQL + PostGIS, lưu dữ liệu
│── progress.py # Theo dõi & resume tiến trình scraping
│── requirements.txt # Thư viện cần cài đặt
│── README.md # Tài liệu mô tả (file này)


---

## 🔄 Quy trình scraping

1. **Sinh query tìm kiếm**  
   Ghép: `keyword + district + province` từ `config.py`.

2. **Mở Google Maps bằng Selenium**  
   - `scraper.py` nhập query vào ô tìm kiếm.  
   - Xử lý captcha & các lỗi mạng.  

3. **Cuộn kết quả**  
   - `scroll.py` cuộn xuống để tải đủ danh sách cửa hàng.

4. **Parse dữ liệu từng cửa hàng**  
   - `parser.py` trích xuất:  
     - `name`, `category`, `place_id`  
     - `lat`, `lng`, `image`  
     - `status`, `closing_time`  
     - `phone`, `map_url`  

5. **Lấy địa chỉ chi tiết**  
   - `geocode.py` chuyển toạ độ → địa chỉ chính xác.  
   - Kiểm tra xem có thuộc tỉnh/huyện mục tiêu hay không.

6. **Lưu dữ liệu vào PostgreSQL**  
   - `db.py` lưu vào bảng `grocery_stores`.  
   - `progress.py` ghi trạng thái (`running`, `done`, `failed`) để resume dễ dàng.

---

## 🛠️ Chuẩn hoá dữ liệu

Sau khi thu thập, dữ liệu được chuẩn hoá sang bảng **`shops_clean`**:

| Cột           | Mô tả                                                |
|---------------|-------------------------------------------------------|
| `shop_type`   | Chuẩn về: `drugstore` hoặc `agri_supply`             |
| `status`      | Chuẩn về: `open`, `closed`, `temp_closed`, `unknown` |
| `geom`        | Điểm GPS kiểu `geography(Point,4326)` (PostGIS)      |
| `metadata`    | Giữ thêm `closing_time`, `status_raw`, `category_raw`|

Ngoài ra giữ lại đầy đủ: `name`, `province`, `district`, `address`, `phone`, `rating`, `image`, `map_url`.

👉 Nhờ chuẩn hoá, dữ liệu trở nên đồng bộ, dễ truy vấn & trực quan hoá.

---

## 📊 Kết quả bước 1

- **19.376 cửa hàng** được thu thập thành công.  
- **0 bản ghi thiếu toạ độ.**  
- **0 bản ghi nằm ngoài phạm vi Việt Nam.**  
- Dữ liệu sạch, đã chuẩn bị cho:  
  - **Bước 2:** Loại bỏ trùng lặp.  
  - **Bước 3:** Trực quan hoá độ phủ.  
  - **Bước 4:** Xây dựng công cụ tìm kiếm khách hàng.

---

## 🚀 Demo hình ảnh (minh hoạ pipeline)

```mermaid
flowchart LR
    A[config.py<br/>Danh sách tỉnh, huyện, từ khoá] --> B[scraper.py]
    B --> C[scroll.py<br/>Cuộn danh sách kết quả]
    B --> D[parser.py<br/>Phân tích business card]
    B --> E[geocode.py<br/>Lấy địa chỉ từ tọa độ]
    D --> F[db.py<br/>Lưu PostgreSQL]
    E --> F
    B --> G[progress.py<br/>Theo dõi tiến trình]
    F --> H[(grocery_stores)]
    H --> I[(shops_clean<br/>chuẩn hoá dữ liệu)]

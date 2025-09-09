# 🗺️ Scrape dữ liệu & Lập bản đồ độ phủ điểm bán  
**Ngành hàng: Nhà thuốc (Pharmacy) & Cửa hàng thuốc thú y (Veterinary Pharmacy)**

---

## ⚙️ Cài đặt
```bash
pip install -r requirements.txt
🛠️ Cấu hình
Chỉnh PG_DSN trong config.py để kết nối đúng PostgreSQL/PostGIS.

Nếu chạy server (không cần giao diện Chrome): đặt SELENIUM_HEADLESS=True trong config.py.

▶️ Chạy
bash
Sao chép mã
python scraper.py
🔄 Resume tiến trình
Tiến trình được lưu trong bảng crawl_progress.

Khi chạy lại, scraper sẽ bỏ qua các combo đã done và tiếp tục các combo còn pending/partial.

Muốn làm lại một combo cụ thể:

sql
Sao chép mã
UPDATE crawl_progress
SET status='pending'
WHERE province='Đà Nẵng' AND district='Quận Hải Châu' AND keyword='nhà thuốc';
📂 Cấu trúc dự án
less
Sao chép mã
scrape_data/
│── config.py        # Cấu hình (DSN Postgres, user-agent, headless, danh sách tỉnh/huyện, keywords)
│── scraper.py       # Chương trình chính — khởi tạo Selenium, chạy query, cuộn → parse → geocode → lưu
│── parser.py        # Phân tích 1 card kết quả (name, rating, status, phone, place_id, map_url, lat/lng, image)
│── scroll.py        # Cuộn bền vững danh sách Google Maps
│── geocode.py       # Reverse geocoding: lat/lng → địa chỉ chi tiết (Nominatim OSM, có cache & rate limit)
│── db.py            # Kết nối DB, tạo bảng, lưu dữ liệu, chống trùng
│── progress.py      # Quản lý tiến trình (pending/running/partial/done/failed)
│── requirements.txt # Thư viện Python cần cài
│── README.md        # Hướng dẫn cài đặt, chạy, resume, pipeline đầy đủ
🚀 Pipeline 4 bước
🟢 Bước 1: Thu thập & Chuẩn hoá dữ liệu
Công cụ: Python + Selenium + BeautifulSoup.

Nguồn dữ liệu: Google Maps (query = keyword + district + province).

Thông tin scrape được:

Tên cửa hàng, loại, toạ độ GPS, ảnh, trạng thái, giờ mở/đóng, số điện thoại, place_id, map_url.

Chuẩn hoá:

shop_type: drugstore (nhà thuốc) hoặc vet_shop (thuốc thú y).

status: open, closed, temp_closed, unknown.

geom: geography(Point,4326).

Lưu vào bảng shops_clean.

Kết quả:

~19.000 bản ghi, không thiếu toạ độ, không nằm ngoài Việt Nam.

🟢 Bước 2: Lọc & Loại bỏ trùng lặp
Vấn đề: Cùng một cửa hàng có thể bị scrape nhiều lần (từ nhiều keyword/quận).

Giải pháp:

Dùng place_id để loại trùng tuyệt đối.

Dùng so khớp tên + khoảng cách (ST_DWithin) để loại trùng tương đối.

Kết quả:

Giữ lại bản chính duy nhất cho mỗi cửa hàng.

Cơ sở dữ liệu sạch, không còn trùng lặp.

🟢 Bước 3: Trực quan hoá dữ liệu (Visualization)
Mục tiêu: Hiển thị mật độ/độ phủ điểm bán.

Công cụ:

Kepler.gl (online, nhanh, đẹp).

QGIS (offline, mạnh mẽ).

Leaflet.js + React (xây web app).

Phương pháp:

Hiển thị marker từng cửa hàng (popup chi tiết).

Heatmap/Cluster để xem mật độ.

Choropleth theo tỉnh/huyện (join với shapefile).

Kết quả:______

Bản đồ số thể hiện khu vực nhiều cửa hàng và khu vực còn trống.

Báo cáo mật độ theo tỉnh/huyện hoặc theo lưới 1km.

🟢 Bước 4: Công cụ hỗ trợ doanh nghiệp
Backend (API): FastAPI (Python) hoặc Spring Boot.

/api/shops → lọc theo tỉnh/huyện, loại, trạng thái.

/api/coverage → thống kê độ phủ.

Frontend (Web): React + Leaflet.

Responsive, chạy tốt trên PC & mobile.

Tìm kiếm theo tên, lọc theo tỉnh/huyện, trạng thái, loại hình.

Popup hiển thị thông tin chi tiết (ảnh, giờ mở, số điện thoại, link Google Maps).

Triển khai: chạy local để demo hoặc deploy miễn phí (Render/Railway).

📊 Kết quả & Sản phẩm
✅ Sau 4 bước, nhóm đã hoàn thành:

Cơ sở dữ liệu sạch ghi về Nhà thuốc & Cửa hàng thuốc thú y, đã chuẩn hoá và khử trùng lặp.

Bản đồ số trực quan thể hiện độ phủ theo khu vực, hiển thị chi tiết từng cửa hàng.

Ứng dụng web responsive (React + Leaflet) cho phép tìm kiếm, lọc và xem thông tin cửa hàng.

API backend (FastAPI/Spring Boot) để truy vấn dữ liệu từ PostgreSQL/PostGIS.

Bộ dữ liệu xuất (CSV/GeoJSON) phục vụ phân tích và tích hợp với hệ thống khác.

👉 Đây là công cụ giúp doanh nghiệp và người nghiên cứu dễ dàng:

Nắm bắt khu vực có mật độ cửa hàng cao/thấp.

Xác định thị trường còn trống để mở rộng.

Tìm kiếm và liên hệ nhanh với cửa hàng thuốc & thú y.

🚀 Demo pipeline (Mermaid)
mermaid
Sao chép mã
flowchart LR
    A[config.py<br/>Danh sách tỉnh, huyện, từ khoá] --> B[scraper.py]
    B --> C[scroll.py<br/>Cuộn danh sách kết quả]
    B --> D[parser.py<br/>Parse business card]
    B --> E[geocode.py<br/>Lat/Lng → Địa chỉ]
    D --> F[db.py<br/>Lưu PostgreSQL]
    E --> F
    B --> G[progress.py<br/>Quản lý tiến trình]
    F --> H[(grocery_stores)]
    H --> I[(shops_clean<br/>chuẩn hoá dữ liệu)]
    I --> J[Loại trùng lặp<br/>Bước 2]
    J --> K[Trực quan hoá<br/>Bước 3]
    K --> L[Web App + API<br/>Bước 4]
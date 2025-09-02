# db.py
# Kết nối DB, tạo/migrate bảng, lưu dữ liệu cửa hàng

import psycopg2
import psycopg2.extras
from config import PG_DSN

def connect_postgres():
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    return conn, cur

def ensure_tables(cur, conn):
    # Bảng dữ liệu cửa hàng
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
    # Bảng tiến trình
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crawl_progress (
            province TEXT NOT NULL,
            district TEXT NOT NULL,
            keyword  TEXT NOT NULL,
            status   TEXT NOT NULL DEFAULT 'pending',   -- pending|running|partial|done|failed
            last_place_id TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT crawl_progress_pk PRIMARY KEY (province, district, keyword)
        );
    """)
    # Migrate phòng khi bảng cũ thiếu cột
    cur.execute("ALTER TABLE grocery_stores ADD COLUMN IF NOT EXISTS address TEXT;")
    cur.execute("ALTER TABLE grocery_stores ADD COLUMN IF NOT EXISTS map_url TEXT;")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_province ON grocery_stores (province);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_district ON grocery_stores (district);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gs_latlng ON grocery_stores (latitude, longitude);")

    cur.execute("ALTER TABLE crawl_progress ADD COLUMN IF NOT EXISTS last_place_id TEXT;")
    cur.execute("ALTER TABLE crawl_progress ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending';")
    cur.execute("ALTER TABLE crawl_progress ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();")

    conn.commit()

def is_duplicate(cur, place_id):
    if not place_id or place_id == 'N/A':
        return None
    cur.execute("SELECT * FROM grocery_stores WHERE place_id = %s;", (place_id,))
    return cur.fetchone()

def save_store(cur, conn, store_data):
    """
    Lưu 1 record vào grocery_stores, chống trùng theo place_id.
    Trả về True nếu insert mới, False nếu trùng.
    """
    from psycopg2.extras import DictRow
    existing = is_duplicate(cur, store_data.get("place_id"))
    if existing:
        return False

    cur.execute("""
        INSERT INTO grocery_stores (
            province, district, place_id, name, image, rating, category,
            status, closing_time, phone, latitude, longitude,
            address, map_url, created_at
        ) VALUES (
            %(province)s, %(district)s, %(place_id)s, %(name)s, %(image)s, %(rating)s, %(category)s,
            %(status)s, %(closing_time)s, %(phone)s, %(latitude)s, %(longitude)s,
            %(address)s, %(map_url)s, %(created_at)s
        )
        ON CONFLICT (place_id) DO NOTHING;
    """, store_data)
    conn.commit()
    return cur.rowcount > 0

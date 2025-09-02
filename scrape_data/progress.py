# progress.py
# Quản lý tiến trình crawl theo (province, district, keyword)

def progress_get(cur, province, district, keyword):
    cur.execute("""
        SELECT status, last_place_id, updated_at
        FROM crawl_progress
        WHERE province=%s AND district=%s AND keyword=%s
    """, (province, district, keyword))
    return cur.fetchone()

def progress_upsert(cur, conn, province, district, keyword, status, last_place_id=None):
    cur.execute("""
        INSERT INTO crawl_progress (province, district, keyword, status, last_place_id, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (province, district, keyword) DO UPDATE
          SET status = EXCLUDED.status,
              last_place_id = EXCLUDED.last_place_id,
              updated_at = NOW();
    """, (province, district, keyword, status, last_place_id))
    conn.commit()

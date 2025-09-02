# make_province_districts.py
import json
from urllib.request import urlopen, Request

# v1: bộ dữ liệu "trước sáp nhập 07/2025" (ổn định, phổ biến hiện nay)
API = "https://provinces.open-api.vn/api/v1/?depth=2"

# Nếu bạn muốn thử dữ liệu thử nghiệm "sau sáp nhập 07/2025":
# API = "https://provinces.open-api.vn/api/v2/?depth=2"

# --- B1: Tải đầy đủ tỉnh/thành + quận/huyện ---
req = Request(API, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(req, timeout=60) as r:
    provinces = json.loads(r.read().decode("utf-8"))

# --- B2: Tạo map { "Tên tỉnh/thành": [danh sách quận/huyện] } ---
full_map = {}
for p in provinces:
    pname = (p.get("name") or "").strip()
    dnames = [ (d.get("name") or "").strip()
               for d in (p.get("districts") or [])
               if d.get("name") ]
    dnames = sorted(set(dnames))
    full_map[pname] = dnames

# --- B3: Nếu bạn có sẵn khung JSON như bạn gửi (keys là tỉnh/thành), nạp vào đây ---
user_json_path = "provinces_template.json"  # đổi tên nếu khác
try:
    with open(user_json_path, "r", encoding="utf-8") as f:
        user_template = json.load(f)
except FileNotFoundError:
    # Không có file khung? -> xuất luôn full theo tên API
    with open("PROVINCE_DISTRICTS.json","w",encoding="utf-8") as f:
        json.dump(full_map, f, ensure_ascii=False, indent=2)
    print("✅ Đã tạo PROVINCE_DISTRICTS.json (đầy 63 tỉnh/thành).")
    raise SystemExit(0)

# --- B4: Chuẩn hoá/đồng bộ tên để khớp template của bạn ---
# Lưu ý: Ở cấp tỉnh, API dùng tên chuẩn VD: "Tỉnh Thừa Thiên Huế".
# Nếu template bạn lỡ có "Thành phố Huế" (không phải đơn vị cấp tỉnh),
# mình remap về "Tỉnh Thừa Thiên Huế".
name_fix = {
    "Thành phố Huế": "Tỉnh Thừa Thiên Huế",
}

def normalize_key(k):
    return name_fix.get(k, k)

filled = {}
missing = []   # khóa có trong template nhưng không khớp dữ liệu API
extra   = []   # khóa có trong API nhưng template không có

# Điền theo template người dùng, để giữ đúng các khóa/đặt tên của bạn
for k in user_template.keys():
    kk = normalize_key(k)
    if kk in full_map:
        filled[k] = full_map[kk]
    else:
        filled[k] = []   # giữ nguyên rỗng để bạn dễ kiểm tra
        missing.append(k)

# Gợi ý: nếu muốn thêm cả phần "thừa" (API có nhưng template thiếu), bật đoạn này:
# for kk in sorted(full_map.keys()):
#     if kk not in map(normalize_key, user_template.keys()):
#         extra.append(kk)
#         filled[kk] = full_map[kk]

# --- B5: Xuất file kết quả ---
with open("PROVINCE_DISTRICTS.json","w",encoding="utf-8") as f:
    json.dump(filled, f, ensure_ascii=False, indent=2)

print("✅ Đã tạo PROVINCE_DISTRICTS.json (điền quận/huyện theo template).")
if missing:
    print("⚠️ Không khớp tên (cần bạn kiểm tra):", ", ".join(missing))
# if extra:
#     print("ℹ️ Tên có trong API nhưng ngoài template:", ", ".join(extra))

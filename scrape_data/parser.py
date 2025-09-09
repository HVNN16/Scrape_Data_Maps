# # parser.py
# # Tách và gom logic parse 1 "business card" trong list GMaps.

# import re
# from bs4 import BeautifulSoup

# def categorize(name: str) -> str:
#     n = (name or "").lower()
#     if any(k in n for k in ['nhà thuốc', 'pharmacy', 'quầy thuốc', 'pharmacity', 'hiệu thuốc','đại lý thuốc nam','đại lý thuốc tây','tiệm thuốc','đại lý bán lẻ thuốc','đại lí bán lẻ thuốc','siêu thị thuốc','phamacy','đại lý bán lẻ thuốc']):
#         return 'Nhà thuốc'
#     if any(k in n for k in ['vật tư nông nghiệp', 'cửa hàng vật tư', 'nông dược']):
#         return 'Cửa hàng vật tư nông nghiệp'
#     return 'Khác'

# def parse_business_card(div):
#     """
#     Nhận 1 thẻ <div.Nv2PK> và trích:
#     - name, place_id, map_url, image, rating, status, closing_time, phone
#     - lat, lng (từ href)
#     """
#     # Tên
#     name_tag = div.find('div', class_='qBF1Pd')
#     name = name_tag.text.strip() if name_tag else 'N/A'

#     # URL + place_id + lat/lng
#     place_id = 'N/A'
#     map_url = None
#     lat, lng = None, None
#     link_tag = div.find('a', class_='hfpxzc', href=True)
#     if link_tag and 'href' in link_tag.attrs:
#         map_url = link_tag['href']
#         href = link_tag['href']
#         m = re.search(r'!19s([^?]+)', href) or re.search(r'data=[^!]+!1s([^!]+)', href)
#         if m: place_id = m.group(1)
#         # lat/lng
#         m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', href) or re.search(r'/@(-?\d+\.\d+),(-?\d+\.\d+)', href)
#         if m: lat, lng = m.groups()

#     # Ảnh
#     image_url = 'N/A'
#     img_tag = div.find('img')
#     if img_tag and img_tag.get('src'):
#         image_url = img_tag['src']

#     # Rating
#     rating_tag = div.find('span', class_='MW4etd')
#     rating = rating_tag.text.strip() if rating_tag else 'N/A'

#     # Status / closing_time / phone
#     status, closing_time, phone = 'N/A', 'N/A', 'N/A'
#     info_tags = div.find_all('div', class_='W4Efsd')
#     if len(info_tags) > 1:
#         details_tag = info_tags[1]
#         status_tag = details_tag.find('span', style=lambda v: v and 'rgba(25,134,57' in v)
#         status = status_tag.text.strip() if status_tag else 'N/A'
#         closing_time_tag = details_tag.find('span', style='font-weight: 400;')
#         closing_time = closing_time_tag.text.strip(' ⋅ ').strip() if closing_time_tag else 'N/A'
#         phone_tag = details_tag.find('span', class_='UsdlK')
#         phone = phone_tag.text.strip() if phone_tag else 'N/A'

#     return {
#         "name": name,
#         "category": categorize(name),
#         "place_id": place_id,
#         "map_url": map_url,
#         "image": image_url,
#         "rating": rating,
#         "status": status,
#         "closing_time": closing_time,
#         "phone": phone,
#         "lat": lat,
#         "lng": lng,
#     }

# parser.py
# Tách và gom logic parse 1 "business card" trong list GMaps.

import re
import unicodedata
from bs4 import BeautifulSoup

# ==== Helpers: bỏ dấu để so khớp không dấu ====
def remove_accents(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

# ==== Phân loại cửa hàng ====
def categorize(name: str) -> str:
    n = (name or "").lower().strip()
    n_no = remove_accents(name or "").lower().strip()

    keywords_pharmacy = [
        "nhà thuốc", "hiệu thuốc", "quầy thuốc", "tiệm thuốc",
        "nhà thuốc tây", "nhà thuốc đông y", "nhà thuốc tư nhân",
        "đại lý thuốc tây", "đại lý thuốc nam", "bán lẻ thuốc",
        "siêu thị thuốc", "quầy bán thuốc", "phòng thuốc",
        "thuốc tây", "thuốc nam", "thuốc bắc",
        "pharmacity", "long châu", "an khang", "guardian", "eco",
        "pharmacy", "phamacy", "drugstore", "drug store", "chemist", "medical store"
    ]

    keywords_vet = [
        "thuốc thú y", "nhà thuốc thú y", "cửa hàng thú y",
        "đại lý thuốc thú y", "cửa hàng thuốc cho chó mèo",
        "vật tư thú y", "dụng cụ thú y", "trang thiết bị thú y",
        "phòng khám thú y", "bệnh viện thú y", "trạm thú y",
        "thuốc cho chó", "thuốc cho mèo", "thuốc cho gà",
        "thuốc cho vịt", "thuốc cho heo", "thuốc gia súc", "thuốc gia cầm",
        "vet shop", "vet pharmacy", "veterinary pharmacy", "veterinary drugstore",
        "animal pharmacy", "pet medicine", "pet shop", "pet clinic"
    ]

    if any(k in n for k in keywords_pharmacy) or any(remove_accents(k) in n_no for k in keywords_pharmacy):
        return "Nhà thuốc"
    if any(k in n for k in keywords_vet) or any(remove_accents(k) in n_no for k in keywords_vet):
        return "Cửa hàng thuốc thú y"
    return "Khác"

# ==== Parse business card ====
def parse_business_card(div):
    """
    Nhận 1 thẻ <div.Nv2PK> và trích:
    - name, place_id, map_url, image, rating, status, closing_time, phone
    - lat, lng (từ href)
    """
    # Tên
    name_tag = div.find('div', class_='qBF1Pd')
    name = name_tag.text.strip() if name_tag else 'N/A'

    # URL + place_id + lat/lng
    place_id = 'N/A'
    map_url = None
    lat, lng = None, None
    link_tag = div.find('a', class_='hfpxzc', href=True)
    if link_tag and 'href' in link_tag.attrs:
        map_url = link_tag['href']
        href = link_tag['href']
        # place_id
        m = re.search(r'!19s([^?]+)', href) or re.search(r'data=[^!]+!1s([^!]+)', href)
        if m:
            place_id = m.group(1)
        # lat/lng
        m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', href) or re.search(r'/@(-?\d+\.\d+),(-?\d+\.\d+)', href)
        if m:
            lat, lng = m.groups()

    # Ảnh
    image_url = 'N/A'
    img_tag = div.find('img')
    if img_tag and img_tag.get('src'):
        image_url = img_tag['src']

    # Rating
    rating_tag = div.find('span', class_='MW4etd')
    rating = rating_tag.text.strip() if rating_tag else 'N/A'

    # Status / closing_time / phone
    status, closing_time, phone = 'N/A', 'N/A', 'N/A'
    info_tags = div.find_all('div', class_='W4Efsd')
    if len(info_tags) > 1:
        details_tag = info_tags[1]
        # status có màu xanh (mở cửa) dạng style rgba(25,134,57
        status_tag = details_tag.find('span', style=lambda v: v and 'rgba(25,134,57' in v)
        status = status_tag.text.strip() if status_tag else 'N/A'
        # giờ đóng/mở thường nằm trong span font-weight: 400
        closing_time_tag = details_tag.find('span', style='font-weight: 400;')
        closing_time = closing_time_tag.text.strip(' ⋅ ').strip() if closing_time_tag else 'N/A'
        # phone
        phone_tag = details_tag.find('span', class_='UsdlK')
        phone = phone_tag.text.strip() if phone_tag else 'N/A'

    return {
        "name": name,
        "category": categorize(name),
        "place_id": place_id,
        "map_url": map_url,
        "image": image_url,
        "rating": rating,
        "status": status,
        "closing_time": closing_time,
        "phone": phone,
        "lat": lat,
        "lng": lng,
    }

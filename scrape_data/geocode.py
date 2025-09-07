# geocode.py
# Reverse geocoding từ lat/lng -> địa chỉ chi tiết (display_name OSM)

import time
import requests
from config import OSM_USER_AGENT, OSM_RATE_LIMIT_SLEEP

_cache = {}

def reverse_geocode(lat, lng):
    try:
        if lat in (None, 'N/A', '') or lng in (None, 'N/A', ''):
            return None
        latf = float(lat); lngf = float(lng)
        key = (round(latf, 6), round(lngf, 6))
        if key in _cache:
            return _cache[key]

        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"lat": key[0], "lon": key[1], "format": "jsonv2", "addressdetails": 1}
        headers = {"User-Agent": OSM_USER_AGENT}

        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            addr = resp.json().get("display_name")
            _cache[key] = addr
            time.sleep(OSM_RATE_LIMIT_SLEEP)  
            return addr
        return None
    except Exception:
        return None


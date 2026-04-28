import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://aqarmap.com.eg/en/for-sale/apartment/cairo/",
    "X-Requested-With": "XMLHttpRequest",
}

url = "https://aqarmap.com.eg/api/v3/listing/search"

params = {
    "category": "apartment",
    "purpose": "for-sale", 
    "location": "cairo",
    "page": 1,
    "limit": 20,
}

response = requests.get(url, headers=headers, params=params, timeout=15)
print(f"Status: {response.status_code}")
print(f"Content type: {response.headers.get('content-type')}")
print(response.text[:500])
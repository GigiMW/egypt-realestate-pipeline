import json
import os
import re
from datetime import UTC, datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.dubizzle.com.eg/en/properties/apartments-duplex-for-sale/"
DOMAIN = "https://www.dubizzle.com.eg"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_PAGES = 3
ADS_PER_PAGE = 12

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _now_iso():
    return datetime.now(UTC).isoformat()


def _fetch(url, params=None):
    response = SESSION.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.text


def _unique(values):
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _extract_listing_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for anchor in soup.select('a[href*="/en/ad/"]'):
        href = anchor.get("href")
        if href:
            urls.append(urljoin(DOMAIN, href))
    return _unique(urls)


def _extract_text_lines(soup):
    return [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]


def _match(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _parse_ad(url, page_number):
    html = _fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    lines = _extract_text_lines(soup)

    title_tag = soup.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else None

    json_ld = {}
    ld_tag = soup.find("script", type="application/ld+json")
    if ld_tag:
        try:
            json_ld = json.loads(ld_tag.get_text())
        except json.JSONDecodeError:
            json_ld = {}

    description = json_ld.get("description", "")
    page_text = soup.get_text("\n", strip=True)
    price_amount = _match(r"Price:\s*([0-9,]+)\s*EGP", description) or _match(r"EGP\s*([0-9,]+)", page_text)
    area_value = (
        _match(r"Built-up area:\s*([0-9,]+)\s*sqm", description)
        or _match(r"Bua\s*([0-9,]+)\s*m", description)
        or _match(r"Area \(m[²2]\)\s*([0-9,]+)", page_text)
        or _match(r"Area\s*([0-9,]+)\s*m", page_text)
    )
    bedrooms = _match(r"(\d+)\s+Bedrooms", description) or _match(r"(\d+)\s+beds?", page_text)
    bathrooms = _match(r"(\d+)\s+Bathrooms", description) or _match(r"(\d+)\s+baths?", page_text)

    location = None
    if title and title in lines:
        title_index = lines.index(title)
        if title_index + 1 < len(lines):
            location = lines[title_index + 1]

    if not location and len(lines) > 1:
        location = lines[1]

    return {
        "title": title or json_ld.get("name"),
        "price_raw": f"{price_amount} EGP" if price_amount else None,
        "location": location,
        "area_sqm": f"{area_value} sqm" if area_value else None,
        "bedrooms": int(bedrooms) if bedrooms else None,
        "bathrooms": int(bathrooms) if bathrooms else None,
        "url": url,
        "scraped_at": _now_iso(),
        "page": page_number,
    }


def scrape():
    records = []
    seen_urls = set()

    for page_number in range(1, MAX_PAGES + 1):
        html = _fetch(BASE_URL, params={"page": page_number})
        listing_urls = _extract_listing_urls(html)

        for url in listing_urls[:ADS_PER_PAGE]:
            if url in seen_urls:
                continue

            try:
                record = _parse_ad(url, page_number)
            except Exception as exc:
                print(f"Skipped {url}: {exc}")
                continue

            if record.get("title") and record.get("price_raw"):
                seen_urls.add(url)
                records.append(record)

    print(f"\nTotal scraped: {len(records)}")
    return records


if __name__ == "__main__":
    data = scrape()
    if not data:
        raise RuntimeError("No listings were scraped from Dubizzle")

    os.makedirs("data", exist_ok=True)
    with open("data/raw_listings.json", "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)
    print("Saved to data/raw_listings.json")

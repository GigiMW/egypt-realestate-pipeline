import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

BASE_URL = "https://aqarmap.com.eg/en/for-sale/apartment/cairo/"

def scrape_listings(max_pages=3):
    listings = []
    for page in range(1, max_pages + 1):
        print(f"Scraping page {page}...")
        url = f"{BASE_URL}?page={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed page {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("div[class*='listing-card'], div[class*='property-card'], article")

        for card in cards:
            listing = {}

            title_el = card.select_one("h2, h3, [class*='title']")
            listing["title"] = title_el.get_text(strip=True) if title_el else None

            price_el = card.select_one("[class*='price']")
            listing["price_raw"] = price_el.get_text(strip=True) if price_el else None

            location_el = card.select_one("[class*='location'], [class*='area'], [class*='address']")
            listing["location"] = location_el.get_text(strip=True) if location_el else None

            area_el = card.select_one("[class*='area'], [class*='size'], [class*='sqm']")
            listing["area_sqm"] = area_el.get_text(strip=True) if area_el else None

            link_el = card.select_one("a[href]")
            listing["url"] = link_el["href"] if link_el else None

            listing["scraped_at"] = datetime.utcnow().isoformat()
            listing["page"] = page

            if listing["title"] or listing["price_raw"]:
                listings.append(listing)

    print(f"Total listings scraped: {len(listings)}")
    return listings


def save_listings(listings, output_path="data/raw_listings.json"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    data = scrape_listings(max_pages=3)
    save_listings(data)
import json
import logging
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.dubizzle.com.eg/en/properties/apartments-duplex-for-sale/"
DOMAIN = "https://www.dubizzle.com.eg"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_PAGES = 3
ADS_PER_PAGE = 12
# Resolve paths from the project root so the script works no matter where it is
# launched from (Airflow runs it with a different working directory).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_FILE = os.path.join(DATA_DIR, "raw_listings.json")
# One file per scrape date; together they form the price history.
HISTORY_DIR = os.path.join(DATA_DIR, "history")
MAX_BEDROOMS = 20


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class BlockedError(RuntimeError):
    """Dubizzle answered with its bot-protection page instead of listings."""


def _is_blocked_page(resp):
    return resp.status_code in (403, 429, 503) and "security check" in resp.text[:5000].lower()


def _fetch(url, params=None):
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return ""
    if _is_blocked_page(resp):
        raise BlockedError(
            f"Dubizzle returned its 'Security check' page (HTTP {resp.status_code}). "
            "The site blocks this network (common for cloud/datacenter IPs); "
            "run the scraper from a home connection."
        )
    if not resp.ok:
        logger.error(f"Failed to fetch {url}: HTTP {resp.status_code}")
        return ""
    return resp.text


def _extract_text_lines(soup):
    return [line.strip() for line in soup.get_text("\n").split("\n") if line.strip()]


def _extract_listing_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    return [
        urljoin(DOMAIN, a["href"])
        for a in soup.find_all("a", href=re.compile(r"/en/ad/"))
    ]


def _match(pattern, text):
    if not text:
        return None
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else None


def _clean_location_text(text):
    if not text:
        return None

    cleaned = re.sub(r"\s*,\s*Egypt\s*$", "", str(text), flags=re.IGNORECASE).strip()
    cleaned = cleaned.strip(" ,|-\t\n\r")
    return cleaned or None


def _find_json_value(value, keys):
    if isinstance(value, dict):
        for key in keys:
            candidate = value.get(key)
            if candidate:
                return candidate
        for nested_value in value.values():
            candidate = _find_json_value(nested_value, keys)
            if candidate:
                return candidate
    elif isinstance(value, list):
        for item in value:
            candidate = _find_json_value(item, keys)
            if candidate:
                return candidate
    return None


def _extract_location(json_ld, title, description, page_text):
    candidate = _find_json_value(
        json_ld,
        ("areaServed", "addressLocality", "addressRegion", "location", "contentLocation", "streetAddress"),
    )
    location = _clean_location_text(candidate)
    if location:
        return location

    for text in (title, description, page_text):
        if not text:
            continue
        match = re.search(r"\b(?:in|at|inside|within|on)\s+(.+)", text, re.IGNORECASE)
        if not match:
            continue

        candidate = match.group(1).strip()
        candidate = re.split(r"\s*[|\u2013\u2014]\s*", candidate, maxsplit=1)[0]
        candidate = re.split(
            r"\s+\b(?:in|at|inside|within|on|for sale|for rent|fully|ready|with|by|near|behind|minutes|prime|lowest price|ultra)\b",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        candidate = re.sub(r"\b\d+[mM]\b.*$", "", candidate).strip()
        location = _clean_location_text(candidate)
        if location:
            return location

    return None


def _extract_bedrooms(json_ld, title, description, page_text):
    candidates = [
        _find_json_value(json_ld, ("numberOfBedrooms", "bedrooms", "bedroomCount", "numberOfRooms")),
        title,
        description,
        page_text,
    ]

    # Use [ \t-] instead of \s so a number on the previous line of the page
    # (e.g. the area "133" right above the "Bedrooms" label) is not captured.
    patterns = (
        r"\b(\d{1,2})[ \t-]*bed(?:room)?s?\b",
        r"\bbed(?:room)?s?[ \t]*[:\-]?\s*(\d{1,2})\b",
    )

    for candidate in candidates:
        if isinstance(candidate, (int, float)):
            if 0 < candidate <= MAX_BEDROOMS:
                return int(candidate)
            continue
        if not candidate:
            continue
        for pattern in patterns:
            match = re.search(pattern, str(candidate), re.IGNORECASE)
            if match and 0 < int(match.group(1)) <= MAX_BEDROOMS:
                return int(match.group(1))

    return None


def _parse_ad(url, page_number):
    html = _fetch(url)
    soup = BeautifulSoup(html, "html.parser")

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
        or _match(r"Area \(m²\)\s*([0-9,]+)", page_text)
        or _match(r"Area\s*([0-9,]+)\s*m", page_text)
    )
    bedrooms = _extract_bedrooms(json_ld, title, description, page_text)
    bathrooms = _match(r"(\d+)\s+Bathrooms", description) or _match(r"(\d+)\s+baths?", page_text)

    location = _extract_location(json_ld, title, description, page_text)

    return {
        "title": title,
        "price_raw": f"{price_amount} EGP" if price_amount else None,
        "location": location,
        "area_sqm": f"{area_value} sqm" if area_value else None,
        "bedrooms": bedrooms,
        "bathrooms": int(bathrooms) if bathrooms else None,
        "url": url,
        "scraped_at": _now_iso(),
        "page": page_number,
    }


def scrape():
    logger.info("Starting Dubizzle scraper...")
    records = []
    seen_urls = set()

    for page_number in range(1, MAX_PAGES + 1):
        logger.info(f"Scraping page {page_number}...")
        html = _fetch(BASE_URL, params={"page": page_number})
        listing_urls = _extract_listing_urls(html)

        for url in listing_urls[:ADS_PER_PAGE]:
            if url in seen_urls:
                continue

            try:
                record = _parse_ad(url, page_number)
            except Exception as exc:
                logger.warning(f"Skipped {url}: {exc}")
                continue

            if record.get("title") and record.get("price_raw"):
                seen_urls.add(url)
                records.append(record)

    logger.info(f"Total scraped: {len(records)}")
    return records


if __name__ == "__main__":
    try:
        data = scrape()
        if not data:
            raise RuntimeError("No listings were scraped from Dubizzle")

        os.makedirs(HISTORY_DIR, exist_ok=True)
        snapshot_file = os.path.join(
            HISTORY_DIR, f"raw_listings_{datetime.now(timezone.utc):%Y-%m-%d}.json"
        )
        # raw_listings.json = latest scrape; history/ keeps one file per day
        # (a second run on the same day replaces that day's file).
        for path in (RAW_FILE, snapshot_file):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully scraped {len(data)} listings")
        logger.info(f"Saved to {RAW_FILE} and {snapshot_file}")
    except BlockedError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        raise

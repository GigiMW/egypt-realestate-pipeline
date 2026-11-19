"""Scrape apartment-for-sale listings from Dubizzle Egypt.

Every results page embeds structured data (a schema.org ItemList in a JSON-LD
<script>) with the title, price, size, rooms and address of each ad on the page.
We read that instead of opening every ad, so a run costs one request per results
page (3 by default) rather than one per ad. That is faster, gives cleaner data,
and keeps us well clear of Dubizzle's rate limits on ad pages.
"""

import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.dubizzle.com.eg/en/properties/apartments-duplex-for-sale/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_PAGES = 3

# Be polite: Dubizzle throttles clients that request pages too quickly.
REQUEST_DELAY_SECONDS = (3.0, 5.0)   # random pause between requests
RETRY_BACKOFF_SECONDS = (10, 30)     # waits before each retry on 429/503
MAX_RETRY_AFTER_SECONDS = 60         # longer Retry-After = we're rate-limited; stop

# Resolve paths from the project root so the script works no matter where it is
# launched from (Airflow runs it with a different working directory).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_FILE = os.path.join(DATA_DIR, "raw_listings.json")
# One file per scrape date; together they form the price history.
HISTORY_DIR = os.path.join(DATA_DIR, "history")


class BlockedError(RuntimeError):
    """Dubizzle answered with its bot-protection page instead of listings."""


class RateLimitedError(RuntimeError):
    """Dubizzle asked us to wait longer than we are willing to (Retry-After)."""


SESSION = requests.Session()
SESSION.headers.update(HEADERS)
_last_request_at = 0.0


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def _page_title(text):
    match = re.search(r"<title>(.*?)</title>", text or "", re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else "no title"


def _polite_wait():
    """Keep a random 3-5 s gap between consecutive requests."""
    global _last_request_at
    gap = random.uniform(*REQUEST_DELAY_SECONDS)
    elapsed = time.monotonic() - _last_request_at
    if elapsed < gap:
        time.sleep(gap - elapsed)
    _last_request_at = time.monotonic()


def _fetch(url, params=None):
    """Return the page HTML, or None if it could not be fetched.

    Retries 429/503 with a short back-off. Raises BlockedError on Dubizzle's
    bot-protection page and RateLimitedError when asked to wait over a minute.
    """
    for attempt in range(len(RETRY_BACKOFF_SECONDS) + 1):
        _polite_wait()
        try:
            resp = SESSION.get(url, params=params, timeout=20)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

        if "security check" in _page_title(resp.text).lower():
            raise BlockedError(
                f"Dubizzle returned its 'Security check' page (HTTP {resp.status_code}). "
                "The site is blocking this network or client; try again later or "
                "from a different connection."
            )
        if resp.ok:
            return resp.text

        if resp.status_code in (429, 503) and attempt < len(RETRY_BACKOFF_SECONDS):
            retry_after = resp.headers.get("Retry-After", "")
            wait = int(retry_after) if retry_after.isdigit() else RETRY_BACKOFF_SECONDS[attempt]
            if wait > MAX_RETRY_AFTER_SECONDS:
                raise RateLimitedError(
                    f"Dubizzle rate-limited us (HTTP {resp.status_code}, Retry-After: "
                    f"{wait}s). Stopping; try again after that time."
                )
            logger.warning(f"HTTP {resp.status_code} for {url}; retrying in {wait}s")
            time.sleep(wait)
            continue

        logger.error(f"Failed to fetch {url}: HTTP {resp.status_code} ({_page_title(resp.text)!r})")
        return None
    return None


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _json_ld_documents(html):
    """Parsed content of every JSON-LD <script> on the page."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all("script", type=re.compile(r"ld\+json", re.IGNORECASE)):
        raw = tag.string or tag.get_text() or ""
        try:
            yield json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.debug(f"Skipping unparsable JSON-LD block: {exc}")


def _walk(node):
    """Every dict nested anywhere inside a JSON value (depth-first)."""
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _types(node):
    t = node.get("@type")
    return set(t) if isinstance(t, list) else {t}


def _describe_json_ld(html):
    """Short summary of the JSON-LD on a page, for error messages."""
    found = sorted({str(t) for doc in _json_ld_documents(html) for n in _walk(doc) for t in _types(n) if t})
    return ", ".join(found[:15]) or "none"


def _listing_items(html):
    """The listing entries from the page's schema.org ItemList(s).

    The ItemList may sit at the top level or be nested inside another object
    (e.g. a CollectionPage), so the whole JSON tree is searched.
    """
    blocks = (n for doc in _json_ld_documents(html) for n in _walk(doc))
    for block in blocks:
        if "ItemList" not in _types(block):
            continue
        for element in block.get("itemListElement") or []:
            item = element.get("item") if isinstance(element, dict) else None
            if isinstance(item, dict) and item.get("url"):
                yield item


def _as_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_listing(item, page_number, scraped_at):
    """Turn one schema.org RealEstateListing into our raw record format.

    Returns None when the ad has no title or price (nothing to analyse).
    """
    entity = item.get("mainEntity") or {}
    offer = item.get("offers") or {}
    if isinstance(offer, list):
        offer = offer[0] if offer else {}
    address = entity.get("address") or {}
    floor = entity.get("floorSize") or {}

    title = (item.get("name") or entity.get("name") or "").strip() or None
    price = _as_int(offer.get("price"))
    if not title or not price or (offer.get("priceCurrency") or "EGP") != "EGP":
        return None

    size = _as_int(floor.get("value")) if isinstance(floor, dict) else None
    compound = (address.get("streetAddress") or "").strip() or None
    locality = (address.get("addressLocality") or "").strip() or None

    return {
        "title": title,
        # Kept as text in the same format as before ("3,950,000 EGP" / "157 sqm")
        # so older snapshots and the dbt staging model stay compatible.
        "price_raw": f"{price:,} EGP",
        "location": ", ".join(p for p in (compound, locality) if p) or None,
        "area_sqm": f"{size} sqm" if size else None,
        "bedrooms": _as_int(entity.get("numberOfBedrooms")),
        "bathrooms": _as_int(entity.get("numberOfBathroomsTotal")),
        "url": item["url"],
        "scraped_at": scraped_at,
        "page": page_number,
    }


def parse_results_page(html, page_number, scraped_at):
    """All listings on one results page."""
    records = []
    for item in _listing_items(html):
        record = parse_listing(item, page_number, scraped_at)
        if record:
            records.append(record)
    return records


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def scrape():
    logger.info("Starting Dubizzle scraper...")
    scraped_at = datetime.now(timezone.utc).isoformat()
    records, seen_urls = [], set()

    for page_number in range(1, MAX_PAGES + 1):
        logger.info(f"Scraping results page {page_number}...")
        try:
            html = _fetch(BASE_URL, params={"page": page_number})
        except RateLimitedError as exc:
            logger.error(str(exc))
            break
        if html is None:
            logger.error(f"Could not load results page {page_number}; stopping.")
            break

        page_records = parse_results_page(html, page_number, scraped_at)
        if not page_records:
            logger.error(
                f"No listings found in the structured data on page {page_number}. "
                "Dubizzle may have changed its page layout. "
                f"JSON-LD types on the page: {_describe_json_ld(html)}"
            )
            break

        new = [r for r in page_records if r["url"] not in seen_urls]
        seen_urls.update(r["url"] for r in new)
        records.extend(new)
        logger.info(f"  {len(new)} listings on page {page_number} (total {len(records)})")

    logger.info(f"Total scraped: {len(records)}")
    return records


def save_snapshot(data):
    """Write the scrape to raw_listings.json and today's history file."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    snapshot_file = os.path.join(
        HISTORY_DIR, f"raw_listings_{datetime.now(timezone.utc):%Y-%m-%d}.json"
    )
    # raw_listings.json = latest scrape; history/ keeps one file per day
    # (a second run on the same day replaces that day's file).
    for path in (RAW_FILE, snapshot_file):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(data)} listings to {RAW_FILE} and {snapshot_file}")


def check_saved_page(path):
    """Parse a results page saved earlier today and print what was found (no network)."""
    with open(path, encoding="utf-8") as f:
        html = f.read()
    # Use the file's modification time as the scrape time.
    saved_at = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat()
    records = parse_results_page(html, 1, saved_at)
    print(f"{len(records)} listings found in {path}")
    print(f"JSON-LD types on the page: {_describe_json_ld(html)}")
    for r in records[:5]:
        print(f"  {r['price_raw']:>16} | {r['area_sqm'] or '?':>8} | {r['location']} | {r['title'][:50]}")
    return records


if __name__ == "__main__":
    import sys

    # python dubizzle_scraper.py --file page.html [--save]
    #   Parse a results page saved earlier (e.g. while rate-limited). With
    #   --save, store it as today's snapshot, like a normal scrape would.
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--file":
        found = check_saved_page(sys.argv[2])
        if found and sys.argv[3:] == ["--save"]:
            save_snapshot(found)
        raise SystemExit(0 if found else 1)

    try:
        data = scrape()
        if not data:
            raise RuntimeError("No listings were scraped from Dubizzle")

        logger.info(f"Successfully scraped {len(data)} listings")
        save_snapshot(data)
    except BlockedError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        raise

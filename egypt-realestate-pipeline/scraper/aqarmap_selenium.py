from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import json, os, time
from datetime import datetime, UTC

def scrape():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    driver = webdriver.Edge(
        service=Service(EdgeChromiumDriverManager().install()),
        options=options
    )

    listings = []

    for page in range(1, 4):
        url = f"https://aqarmap.com.eg/en/for-sale/apartment/cairo/?page={page}"
        print(f"Loading page {page}: {url}")
        driver.get(url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='listing'], [class*='property'], [class*='card']"))
            )
        except:
            print(f"  Timeout on page {page}")

        time.sleep(3)

        cards = driver.find_elements(By.CSS_SELECTOR, "[class*='listing-card'], [class*='property-card'], [class*='PropertyCard'], [class*='ListingCard']")
        print(f"  Found {len(cards)} cards")

        for card in cards:
            try:
                listing = {}
                try:
                    listing["title"] = card.find_element(By.CSS_SELECTOR, "h2,h3,[class*='title']").text.strip()
                except: listing["title"] = None
                try:
                    listing["price_raw"] = card.find_element(By.CSS_SELECTOR, "[class*='price'],[class*='Price']").text.strip()
                except: listing["price_raw"] = None
                try:
                    listing["location"] = card.find_element(By.CSS_SELECTOR, "[class*='location'],[class*='area'],[class*='district']").text.strip()
                except: listing["location"] = None
                try:
                    listing["area_sqm"] = card.find_element(By.CSS_SELECTOR, "[class*='area'],[class*='size'],[class*='sqm']").text.strip()
                except: listing["area_sqm"] = None
                try:
                    listing["url"] = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                except: listing["url"] = None

                listing["scraped_at"] = datetime.now(UTC).isoformat()
                listing["page"] = page

                if listing["title"] or listing["price_raw"]:
                    listings.append(listing)
            except Exception as e:
                continue

    driver.quit()
    print(f"\nTotal scraped: {len(listings)}")
    return listings

if __name__ == "__main__":
    data = scrape()
    os.makedirs("data", exist_ok=True)
    with open("data/raw_listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Saved to data/raw_listings.json")
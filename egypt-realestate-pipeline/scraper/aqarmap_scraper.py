import requests
import json
import os
from datetime import datetime, UTC

BASE_URL = "https://api.worldbank.org/v2/country/EG/indicator"

INDICATORS = {
    "cpi": {
        "code": "FP.CPI.TOTL",
        "name": "Consumer Price Index (2010=100)",
        "description": "Measures inflation in Egypt over time"
    },
    "urban_population": {
        "code": "SP.URB.TOTL",
        "name": "Urban Population",
        "description": "Total urban population in Egypt"
    },
    "gdp_per_capita": {
        "code": "NY.GDP.PCAP.CD",
        "name": "GDP Per Capita (USD)",
        "description": "GDP per capita in current USD"
    },
    "real_interest_rate": {
        "code": "FR.INR.RINR",
        "name": "Real Interest Rate (%)",
        "description": "Real interest rate - proxy for mortgage cost"
    },
    "inflation": {
        "code": "FP.CPI.TOTL.ZG",
        "name": "Inflation Rate (%)",
        "description": "Annual inflation rate in Egypt"
    },
}

def fetch_indicator(indicator_key, indicator_info):
    print(f"Fetching {indicator_info['name']}...")
    url = f"{BASE_URL}/{indicator_info['code']}"
    params = {
        "format": "json",
        "per_page": 60,
        "mrv": 30,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        if not isinstance(raw, list) or len(raw) < 2:
            print(f"  Unexpected response format")
            return []

        records = []
        for item in raw[1]:
            if item.get("value") is None:
                continue
            records.append({
                "indicator_key":  indicator_key,
                "indicator_code": indicator_info["code"],
                "indicator_name": indicator_info["name"],
                "country":        item["country"]["value"],
                "country_code":   item["countryiso3code"],
                "year":           int(item["date"]),
                "value":          float(item["value"]),
                "unit":           item.get("unit", ""),
                "scraped_at":     datetime.now(UTC).isoformat(),
            })

        print(f"  Got {len(records)} records")
        return records

    except Exception as e:
        print(f"  Error: {e}")
        return []


def fetch_all():
    all_records = []
    for key, info in INDICATORS.items():
        records = fetch_indicator(key, info)
        all_records.extend(records)

    print(f"\nTotal records fetched: {len(all_records)}")
    return all_records


def save(data, path="data/raw_indicators.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved to {path}")


if __name__ == "__main__":
    data = fetch_all()
    save(data)
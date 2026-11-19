"""Unit tests for the Dubizzle results-page parser (no network access)."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scraper"))

import dubizzle_scraper as scraper  # noqa: E402

SCRAPED_AT = "2026-11-19T20:00:00+00:00"


@pytest.fixture
def page_html():
    with open(os.path.join(HERE, "fixtures", "results_page.html"), encoding="utf-8") as f:
        return f.read()


def test_parses_every_priced_listing(page_html):
    records = scraper.parse_results_page(page_html, 1, SCRAPED_AT)
    # The third ad has no price and must be skipped.
    assert len(records) == 2


def test_record_fields(page_html):
    first = scraper.parse_results_page(page_html, 1, SCRAPED_AT)[0]
    assert first == {
        "title": "An apartment near delivery and very close to all services, ready for viewing.",
        "price_raw": "3,950,000 EGP",
        "location": "BOARDWALK, New Capital City",
        "area_sqm": "157 sqm",
        "bedrooms": 3,
        "bathrooms": 2,
        "url": "https://www.dubizzle.com.eg/ad/an-apartment-near-delivery-and-very-close-to-all-services-ready-for-viewing-ID504356445.html",
        "scraped_at": SCRAPED_AT,
        "page": 1,
    }


def test_price_given_as_string(page_html):
    second = scraper.parse_results_page(page_html, 2, SCRAPED_AT)[1]
    assert second["price_raw"] == "8,500,000 EGP"
    assert second["location"] == "Mountain View 1.1, New Cairo"
    assert second["page"] == 2


def test_page_without_structured_data_returns_nothing():
    assert scraper.parse_results_page("<html><title>x</title></html>", 1, SCRAPED_AT) == []


def test_security_check_page_raises(monkeypatch):
    class Resp:
        status_code, ok, headers = 503, False, {}
        text = "<title>Security check | Dubizzle</title>"

    monkeypatch.setattr(scraper.SESSION, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(scraper, "REQUEST_DELAY_SECONDS", (0, 0))
    with pytest.raises(scraper.BlockedError):
        scraper._fetch(scraper.BASE_URL)


def test_long_retry_after_stops_instead_of_sleeping(monkeypatch):
    class Resp:
        status_code, ok, text = 503, False, ""
        headers = {"Retry-After": "3600"}

    monkeypatch.setattr(scraper.SESSION, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(scraper, "REQUEST_DELAY_SECONDS", (0, 0))
    monkeypatch.setattr(scraper.time, "sleep", lambda s: pytest.fail(f"slept {s}s"))
    with pytest.raises(scraper.RateLimitedError):
        scraper._fetch(scraper.BASE_URL)

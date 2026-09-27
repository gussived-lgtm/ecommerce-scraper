"""
E-commerce scraper (demo).

Scrapes a product catalogue (title, price, rating, availability, URL),
handles pagination and transient network errors, and exports the result
to both CSV and Excel via pandas.

Target: http://books.toscrape.com  -- a public sandbox site built for
practising web scraping, so no terms-of-service are violated.

Usage:
    python scraper.py                      # scrape all pages -> books.csv / books.xlsx
    python scraper.py --max-pages 5        # only the first 5 pages
    python scraper.py --out products       # write products.csv / products.xlsx
    python scraper.py --delay 1.0          # 1s pause between requests (be polite)
"""

import argparse
import logging
import re
import sys
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "http://books.toscrape.com/"
START_PAGE = "catalogue/page-1.html"

# A real browser User-Agent. Many sites reject the default python-requests one,
# so sending a normal UA is the first, cheapest anti-blocking measure.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# The site renders the rating as a CSS class word ("Three"); map it to a number.
RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")


def make_session() -> requests.Session:
    """Session with a browser UA and automatic retries on flaky responses."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Retry a few times on connection errors and 5xx/429, backing off each time.
    # This is what keeps a long scrape alive when the server hiccups.
    retry = Retry(
        total=4,
        backoff_factor=1.0,  # waits 0s, 1s, 2s, 4s between attempts
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def parse_price(text: str) -> float | None:
    """'£51.77' -> 51.77 . Strips currency symbols and any stray bytes."""
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def parse_book(pod) -> dict:
    """Extract one product from an <article class="product_pod"> element."""
    link = pod.select_one("h3 a")
    price = pod.select_one("p.price_color")
    availability = pod.select_one("p.instock.availability")
    rating = pod.select_one("p.star-rating")

    # rating class looks like ["star-rating", "Three"] -> take the word
    rating_word = ""
    if rating:
        rating_word = next(
            (c for c in rating.get("class", []) if c != "star-rating"), ""
        )

    return {
        "title": link["title"].strip() if link else "",
        "price_gbp": parse_price(price.get_text()) if price else None,
        "rating": RATING_WORDS.get(rating_word),
        "in_stock": bool(availability and "in stock" in availability.get_text().lower()),
        "url": urljoin(BASE_URL + "catalogue/", link["href"]) if link else "",
    }


def scrape_page(session: requests.Session, url: str) -> tuple[list[dict], str | None]:
    """Return (books on this page, absolute URL of the next page or None)."""
    response = session.get(url, timeout=15)
    response.raise_for_status()
    response.encoding = "utf-8"  # the site mislabels its encoding otherwise

    soup = BeautifulSoup(response.text, "lxml")
    books = [parse_book(pod) for pod in soup.select("article.product_pod")]

    next_link = soup.select_one("li.next a")
    next_url = urljoin(url, next_link["href"]) if next_link else None
    return books, next_url


def scrape_all(max_pages: int | None, delay: float) -> list[dict]:
    """Walk the catalogue page by page until it ends or max_pages is reached."""
    session = make_session()
    url = urljoin(BASE_URL, START_PAGE)
    all_books: list[dict] = []
    page_num = 0

    while url:
        page_num += 1
        log.info("Page %d: %s", page_num, url)
        try:
            books, url = scrape_page(session, url)
        except requests.RequestException as exc:
            # Do not swallow errors silently: log and stop cleanly with what we have.
            log.error("Failed on page %d (%s): %s", page_num, url, exc)
            break

        all_books.extend(books)
        log.info("  found %d books (total %d)", len(books), len(all_books))

        if max_pages and page_num >= max_pages:
            log.info("Reached max-pages limit (%d), stopping.", max_pages)
            break
        if url:
            time.sleep(delay)  # be polite: space out requests

    return all_books


def save(books: list[dict], out_base: str) -> None:
    """Write the results to <out_base>.csv and <out_base>.xlsx."""
    if not books:
        log.warning("No books scraped, nothing to save.")
        return

    df = pd.DataFrame(books)
    csv_path = f"{out_base}.csv"
    xlsx_path = f"{out_base}.xlsx"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")  # utf-8-sig opens cleanly in Excel
    df.to_excel(xlsx_path, index=False)

    log.info("Saved %d rows -> %s , %s", len(df), csv_path, xlsx_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape a product catalogue to CSV/Excel.")
    parser.add_argument("--max-pages", type=int, default=None, help="limit number of pages")
    parser.add_argument("--out", default="books", help="output file base name (default: books)")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    args = parser.parse_args()

    log.info("Starting scrape of %s", BASE_URL)
    books = scrape_all(max_pages=args.max_pages, delay=args.delay)
    save(books, args.out)
    log.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

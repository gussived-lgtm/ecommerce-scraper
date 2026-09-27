# E-commerce Scraper

A small, readable Python 3 scraper that pulls a product catalogue into clean
CSV and Excel files. Built as a demonstration of a reusable scraping tool.

It collects, for every product:

| Field | Example |
|-------|---------|
| `title` | A Light in the Attic |
| `price_gbp` | 51.77 |
| `rating` | 3 |
| `in_stock` | True |
| `url` | http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html |

**Target site:** [books.toscrape.com](http://books.toscrape.com) — a public
sandbox created specifically for practising web scraping, so no terms of
service are violated. The same structure adapts to a real store on request.

## Features

- Handles **pagination** automatically (follows the "next" link to the end).
- Survives flaky networks: automatic **retries with back-off** on timeouts and
  `429 / 5xx` responses.
- Polite by default: a configurable **delay** between requests and a real
  browser `User-Agent`.
- Clean parsing: prices converted to numbers, ratings converted to 1–5.
- Exports to **both `.csv` and `.xlsx`** via pandas.
- Clear logging so you can see exactly what was fetched.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
# Scrape the whole catalogue -> books.csv and books.xlsx
python scraper.py

# Only the first 5 pages
python scraper.py --max-pages 5

# Custom output name -> products.csv / products.xlsx
python scraper.py --out products

# 1 second between requests (gentler on the server)
python scraper.py --delay 1.0
```

## Arguments

| Argument | Default | Meaning |
|----------|---------|---------|
| `--max-pages` | all | Stop after N pages |
| `--out` | `books` | Base name for the output files |
| `--delay` | `0.5` | Seconds to wait between requests |

## Output

Two files are written next to the script: `<out>.csv` (UTF-8, opens cleanly in
Excel) and `<out>.xlsx`. A full run collects 1000 products in about a minute.

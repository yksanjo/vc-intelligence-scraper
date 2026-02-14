# VC Intelligence Scraper

SEC EDGAR scraper for finding VCs, family offices, and institutional investors.

## Features

- **SEC EDGAR Integration** - Fetches Form ADV, 13F filings
- **Rate Limiting** - Complies with SEC guidelines (10 req/sec)
- **Investor Classification** - Auto-categorizes VC, PE, Family Office, Hedge Fund
- **CSV Export** - Export to CSV for analysis

## Installation

```bash
pip install vc-intelligence-scraper
```

## Usage

```python
from sec_scraper import SECFormADVScraper

scraper = SECFormADVScraper()
advisers = scraper.get_investment_advisers(limit=100)
holders = scraper.get_recent_13f_filers(limit=50)
```

## CLI

```bash
python sec_scraper.py --limit 1000
```

## License

MIT

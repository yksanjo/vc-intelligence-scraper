#!/usr/bin/env python3
"""
SEC EDGAR Form ADV Scraper - Updated for 2026 API
Extracts family office and VC firm data from SEC filings
With rate limiting to comply with SEC guidelines
"""

import requests
import json
import time
import re
import os
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from ratelimit import limits, sleep_and_retry

class SECFormADVScraper:
    """Scrape investment adviser data from SEC EDGAR with rate limiting"""

    # SEC rate limit: 10 requests per second max
    SEC_RATE_LIMIT = 10
    SEC_CALLS_PER_SECOND = 10  # Comply with SEC guidelines

    def __init__(self):
        self.base_url = "https://www.sec.gov"
        self.headers = {
            'User-Agent': 'VC Intelligence Research yoshi@example.com',
            'Accept': 'application/json, text/html, application/xml',
            'Accept-Encoding': 'gzip, deflate',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Rate limiting state
        self.request_times = []
        self.min_request_interval = 1.0 / self.SEC_CALLS_PER_SECOND

    def _rate_limit(self):
        """Apply rate limiting to comply with SEC guidelines"""
        current_time = time.time()
        
        # Remove old request times (older than 1 second)
        self.request_times = [t for t in self.request_times if current_time - t < 1.0]
        
        # If we've made too many requests, wait
        if len(self.request_times) >= self.SEC_CALLS_PER_SECOND:
            sleep_time = 1.0 - (current_time - self.request_times[0])
            if sleep_time > 0:
                print(f"   ⏳ Rate limiting: waiting {sleep_time:.2f}s...")
                time.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(time.time())

    def get_company_tickers(self) -> List[Dict]:
        """Get list of all companies from SEC company tickers JSON"""
        print("📡 Fetching company list from SEC...")

        # SEC provides a JSON file with all company tickers
        url = "https://www.sec.gov/files/company_tickers.json"

        try:
            self._rate_limit()  # Apply rate limiting
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            companies = []
            for key, company in data.items():
                companies.append({
                    'cik': str(company['cik_str']),
                    'name': company['title'],
                    'ticker': company.get('ticker', '')
                })

            print(f"✅ Found {len(companies)} companies")
            return companies

        except Exception as e:
            print(f"❌ Error fetching company list: {e}")
            return []

    def get_investment_advisers(self, limit: int = 200) -> List[Dict]:
        """
        Get investment advisers by searching for common VC/PE/Family Office keywords
        """
        print(f"🔍 Searching for investment advisers (limit: {limit})...")

        companies = self.get_company_tickers()

        # Keywords that indicate investment firms
        investment_keywords = [
            'capital', 'venture', 'partners', 'investment', 'fund',
            'equity', 'management', 'advisors', 'advisory', 'holdings',
            'asset', 'wealth', 'family office', 'trust'
        ]

        advisers = []

        for company in companies:
            name_lower = company['name'].lower()

            # Check if company name contains investment-related keywords
            if any(kw in name_lower for kw in investment_keywords):
                adviser = {
                    'cik': company['cik'],
                    'name': company['name'],
                    'ticker': company.get('ticker', ''),
                    'sec_url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={company['cik']}",
                    'scraped_at': datetime.now().isoformat()
                }
                advisers.append(adviser)

                if len(advisers) >= limit:
                    break

        print(f"✅ Found {len(advisers)} potential investment advisers")
        return advisers

    def get_recent_13f_filers(self, limit: int = 100) -> List[Dict]:
        """
        Get recent 13F filers (institutional investors with $100M+ AUM)
        Uses SEC's full-text search API
        """
        print(f"🔍 Searching for 13F institutional investors...")

        # Use SEC's EFTS (EDGAR Full-Text Search) API
        url = "https://efts.sec.gov/LATEST/search-index"

        params = {
            'q': 'form:13F-HR',
            'dateRange': 'custom',
            'startdt': '2025-01-01',
            'enddt': '2026-12-31',
            'forms': '13F-HR',
        }

        holders = []

        try:
            # Alternative: Use the company search
            search_url = f"{self.base_url}/cgi-bin/browse-edgar"
            params = {
                'action': 'getcurrent',
                'type': '13F-HR',
                'company': '',
                'dateb': '',
                'owner': 'include',
                'count': limit,
                'output': 'atom'
            }

            self._rate_limit()  # Apply rate limiting
            response = self.session.get(search_url, params=params, timeout=30)

            if response.status_code == 200:
                content = response.text

                # Parse Atom feed for company info
                # Extract entries
                entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)

                for entry in entries[:limit]:
                    # Extract company name
                    name_match = re.search(r'<title[^>]*>([^<]+)</title>', entry)
                    cik_match = re.search(r'CIK=(\d+)', entry)

                    if name_match and cik_match:
                        name = name_match.group(1).strip()
                        cik = cik_match.group(1)

                        # Clean up name (remove form type suffix)
                        name = re.sub(r'\s*\(13F-HR.*?\)\s*$', '', name)
                        name = re.sub(r'\s*13F-HR.*$', '', name)

                        holders.append({
                            'cik': cik,
                            'name': name.strip(),
                            'filing_type': '13F-HR',
                            'sec_url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F-HR",
                            'scraped_at': datetime.now().isoformat()
                        })

            print(f"✅ Found {len(holders)} 13F filers")

        except Exception as e:
            print(f"❌ Error searching 13F holders: {e}")

        return holders

    def get_adviser_details(self, cik: str) -> Optional[Dict]:
        """Get detailed company information from SEC with rate limiting"""

        # Apply rate limiting
        self._rate_limit()

        # Use SEC's company facts API
        cik_padded = cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

        try:
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()

                addresses = data.get('addresses', {})
                business = addresses.get('business', {})

                return {
                    'address': f"{business.get('street1', '')} {business.get('street2', '')}, {business.get('city', '')}, {business.get('stateOrCountry', '')} {business.get('zipCode', '')}".strip(),
                    'city': business.get('city', ''),
                    'state': business.get('stateOrCountry', ''),
                    'phone': data.get('phone', ''),
                    'sic': data.get('sic', ''),
                    'sic_description': data.get('sicDescription', ''),
                }

        except Exception as e:
            pass

        return None

    def classify_investor_type(self, name: str, sic_desc: str = '') -> str:
        """Classify investor based on name and SIC patterns"""
        name_lower = name.lower()
        sic_lower = sic_desc.lower() if sic_desc else ''
        combined = f"{name_lower} {sic_lower}"

        # Family office indicators
        if any(kw in combined for kw in ['family', 'office', 'trust', 'estate']):
            return 'Family Office'

        # VC indicators
        if any(kw in combined for kw in ['venture', 'ventures', 'seed', 'startup']):
            return 'Venture Capital'

        # PE indicators
        if any(kw in combined for kw in ['private equity', 'buyout', 'leveraged']):
            return 'Private Equity'

        # Hedge fund indicators
        if any(kw in combined for kw in ['hedge', 'offshore', 'alternative']):
            return 'Hedge Fund'

        # Asset management
        if any(kw in combined for kw in ['asset management', 'wealth', 'advisory']):
            return 'Asset Management'

        # Investment company
        if any(kw in combined for kw in ['capital', 'partners', 'fund', 'investment']):
            return 'Investment Company'

        return 'Other Institutional'

    def extract_state(self, address: str) -> Optional[str]:
        """Extract US state code from address"""
        if not address:
            return None

        states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC']

        for state in states:
            if f' {state} ' in address or f', {state}' in address or address.endswith(f' {state}'):
                return state

        return None


def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 SEC EDGAR INVESTMENT INTELLIGENCE SCRAPER")
    print("=" * 60)
    print()

    scraper = SECFormADVScraper()

    # Collect data
    all_investors = []
    seen_ciks = set()

    # Get investment advisers from company list
    print("\n📊 Phase 1: Investment Advisers from Company Registry")
    print("-" * 60)
    advisers = scraper.get_investment_advisers(limit=150)

    for adviser in advisers:
        if adviser['cik'] not in seen_ciks:
            seen_ciks.add(adviser['cik'])
            all_investors.append(adviser)

    # Get 13F holders (institutional investors)
    print("\n📊 Phase 2: 13F Institutional Holders")
    print("-" * 60)
    holders = scraper.get_recent_13f_filers(limit=100)

    for holder in holders:
        if holder['cik'] not in seen_ciks:
            seen_ciks.add(holder['cik'])
            all_investors.append(holder)

    # Enrich with details
    print("\n📊 Phase 3: Enriching investor data...")
    print("-" * 60)

    for i, investor in enumerate(all_investors):
        if i % 20 == 0:
            print(f"   Processing {i+1}/{len(all_investors)}...")
            time.sleep(0.2)  # Rate limiting

        details = scraper.get_adviser_details(investor['cik'])
        if details:
            investor.update(details)

        # Classify investor type
        investor['type'] = scraper.classify_investor_type(
            investor['name'],
            investor.get('sic_description', '')
        )

        # Extract state
        if not investor.get('state'):
            investor['state'] = scraper.extract_state(investor.get('address', ''))

    # Create DataFrame
    df = pd.DataFrame(all_investors)

    # Summary statistics
    print("\n" + "=" * 60)
    print("📈 RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total investors found: {len(df)}")
    print("\nBreakdown by type:")
    if 'type' in df.columns and len(df) > 0:
        print(df['type'].value_counts().to_string())

    # Save to CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'vc_database.csv')
    df.to_csv(output_file, index=False)
    print(f"\n💾 Data saved to: {output_file}")

    # Show sample records
    if len(df) > 0:
        print("\n📋 Sample Records:")
        print("-" * 60)
        print(df[['name', 'type', 'state']].head(10).to_string(index=False))

    return df

if __name__ == "__main__":
    df = main()

#!/usr/bin/env python3
"""
SF Tennis Courts URL Scraper

A simple scraper that pulls and parses URLs from the SF Rec & Park tennis courts page
using only requests and BeautifulSoup.
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
from collections import Counter
import os

class SFTennisURLScraper:
    def __init__(self):
        self.base_url = "https://sfrecpark.org/1446/Reservable-Tennis-Courts"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.html_content = None
        self.urls = []
        
    def fetch_page(self):
        """Fetch the tennis courts page and store HTML content"""
        print(f"Fetching: {self.base_url}")
        
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            self.html_content = response.text
            print(f"✅ Successfully fetched page ({len(self.html_content)} characters)")
            
            # Save HTML for reference
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_filename = f"tennis_courts_page_{timestamp}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(self.html_content)
            print(f"💾 HTML saved to: {html_filename}")
            
            return True
            
        except requests.RequestException as e:
            print(f"❌ Error fetching page: {e}")
            return False
    
    def parse_urls(self):
        """Parse all URLs from the page"""
        if not self.html_content:
            print("❌ No HTML content to parse")
            return []
        
        print("\n🔍 Parsing URLs from page...")
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        # Find all links
        links = soup.find_all('a', href=True)
        print(f"Found {len(links)} total links")
        
        # Extract and process URLs
        urls = []
        for link in links:
            href = link.get('href')
            if href:
                # Convert relative URLs to absolute
                full_url = urljoin(self.base_url, href)
                urls.append({
                    'url': full_url,
                    'text': link.get_text(strip=True),
                    'title': link.get('title', ''),
                    'class': link.get('class', [])
                })
        
        self.urls = urls
        print(f"✅ Extracted {len(urls)} URLs")
        return urls
    
    def analyze_urls(self):
        """Analyze the URLs to find tennis court related ones"""
        if not self.urls:
            print("❌ No URLs to analyze")
            return
        
        print("\n📊 Analyzing URLs...")
        
        # Filter for tennis/court related URLs
        tennis_keywords = ['tennis', 'court', 'rec.us', 'reservation', 'booking']
        tennis_urls = []
        
        # URL to exclude (the original page)
        excluded_url = "https://sfrecpark.org/1446/Reservable-Tennis-Courts"
        
        for url_data in self.urls:
            url = url_data['url'].lower()
            text = url_data['text'].lower()
            
            # Skip the original URL
            if url_data['url'] == excluded_url:
                continue
                
            if any(keyword in url or keyword in text for keyword in tennis_keywords):
                tennis_urls.append(url_data)
        
        print(f"🎾 Found {len(tennis_urls)} tennis-related URLs")
        
        # Group by domain
        domains = Counter()
        unique_urls = set()
        
        for url_data in tennis_urls:
            parsed = urlparse(url_data['url'])
            domain = parsed.netloc
            domains[domain] += 1
            unique_urls.add(url_data['url'])
        
        print(f"\n📈 URL Analysis:")
        print(f"  Total tennis URLs: {len(tennis_urls)}")
        print(f"  Unique URLs: {len(unique_urls)}")
        print(f"  Domains found:")
        for domain, count in domains.most_common():
            print(f"    {domain}: {count} URLs")
        
        # Show sample URLs
        print(f"\n🔗 Sample tennis URLs:")
        for i, url_data in enumerate(tennis_urls[:10]):
            print(f"  {i+1}. {url_data['text']} -> {url_data['url']}")
        
        if len(tennis_urls) > 10:
            print(f"  ... and {len(tennis_urls) - 10} more")
        
        return tennis_urls
    
    def save_results(self, tennis_urls):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            'timestamp': timestamp,
            'base_url': self.base_url,
            'total_urls_found': len(self.urls),
            'tennis_urls_count': len(tennis_urls),
            'tennis_urls': tennis_urls,
            'all_urls': self.urls
        }
        
        filename = f"tennis_urls_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename
    
    def run(self):
        """Run the complete scraping process"""
        print("🎾 SF Tennis Courts URL Scraper")
        print("=" * 40)
        
        # Fetch the page
        if not self.fetch_page():
            return False
        
        # Parse URLs
        self.parse_urls()
        
        # Analyze URLs
        tennis_urls = self.analyze_urls()
        
        # Save results
        if tennis_urls:
            self.save_results(tennis_urls)
        
        print(f"\n✅ Scraping complete!")
        print(f"   Total URLs found: {len(self.urls)}")
        print(f"   Tennis URLs: {len(tennis_urls) if tennis_urls else 0}")
        
        return True

def main():
    scraper = SFTennisURLScraper()
    scraper.run()

if __name__ == "__main__":
    main()

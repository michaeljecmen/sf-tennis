#!/usr/bin/env python3
"""
Fetch Alice Marble Tennis Court page
"""

import requests
from datetime import datetime

def fetch_alice_marble():
    """Fetch the Alice Marble tennis court page"""
    url = "https://rec.us/alicemarble"
    
    # Set up session with headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    print(f"Fetching: {url}")
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        print(f"✅ Successfully fetched page ({len(response.text)} characters)")
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'Unknown')}")
        
        # Save HTML for inspection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = f"alice_marble_{timestamp}.html"
        
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"💾 HTML saved to: {html_filename}")
        
        # Show first few lines for preview
        lines = response.text.split('\n')
        print(f"\n📄 First 10 lines preview:")
        for i, line in enumerate(lines[:10], 1):
            print(f"{i:2d}: {line}")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error fetching page: {e}")
        return False

if __name__ == "__main__":
    fetch_alice_marble()

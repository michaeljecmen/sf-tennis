#!/usr/bin/env python3
"""
Tennis Court Availability Checker

Automates Firefox to check tennis court availability on SF Rec & Park pages.
"""

import time
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class TennisAvailabilityChecker:
    def __init__(self, use_existing_session=True):
        self.driver = None
        self.use_existing_session = use_existing_session
        
    def setup_driver(self):
        """Set up Firefox driver with options"""
        firefox_options = Options()
        
        # Set user agent
        firefox_options.set_preference("general.useragent.override", 
                                     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Set Firefox binary path
        firefox_options.binary_location = "/Applications/Firefox.app/Contents/MacOS/firefox"
        
        # Disable images for faster loading (optional)
        firefox_options.set_preference("permissions.default.image", 2)
        
        try:
            print("🔄 Starting new Firefox session...")
            self.driver = webdriver.Firefox(options=firefox_options)
            print("✅ Firefox driver initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Error initializing Firefox driver: {e}")
            return False
    
    def check_tennis_availability(self, url, court_name="Tennis Court"):
        """Check availability for a specific tennis court page"""
        if not self.driver:
            print("❌ Driver not initialized")
            return None
        
        print(f"\n🎾 Checking availability for: {court_name}")
        print(f"📍 URL: {url}")
        
        try:
            # Navigate to the page
            self.driver.get(url)
            print("📄 Page loaded, waiting for content to render...")
            
            # Wait for the page to load and render
            wait = WebDriverWait(self.driver, 15)
            
            # Wait for either availability info or a specific element
            try:
                # Look for availability information
                availability_elements = wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'No free spots available')]")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'available')]")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'reservation')]")),
                        EC.presence_of_element_located((By.CLASS_NAME, "tennis")),
                        EC.presence_of_element_located((By.CLASS_NAME, "court"))
                    )
                )
                print("✅ Page content loaded")
            except TimeoutException:
                print("⚠️  Timeout waiting for content, but continuing...")
            
            # Give it a bit more time for dynamic content
            time.sleep(3)
            
            # Extract availability information
            availability_info = self.extract_availability_info()
            
            # Save the rendered HTML for inspection (only if it doesn't exist)
            html_filename = f"{court_name.lower().replace(' ', '_')}_rendered.html"
            if not os.path.exists(html_filename):
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                print(f"💾 Rendered HTML saved to: {html_filename}")
            else:
                print(f"📄 HTML file already exists: {html_filename}")
            
            # Close the current tab
            self.driver.close()
            print("🔒 Tab closed")
            
            return availability_info
            
        except Exception as e:
            print(f"❌ Error checking availability: {e}")
            return None
    
    def extract_availability_info(self):
        """Extract availability information from the rendered page"""
        try:
            # Get the full page source
            page_source = self.driver.page_source
            
            # Look for availability indicators
            availability_info = {
                'timestamp': datetime.now().isoformat(),
                'has_availability': False,
                'availability_text': '',
                'next_available': '',
                'operating_hours': '',
                'location_name': '',
                'raw_text_found': []
            }
            
            # Common availability text patterns
            availability_patterns = [
                'No free spots available',
                'available',
                'reservation',
                'book now',
                'next available',
                'operating hours',
                '7:30am to 7:30pm'
            ]
            
            # Search for patterns in the page
            for pattern in availability_patterns:
                if pattern.lower() in page_source.lower():
                    availability_info['raw_text_found'].append(pattern)
            
            # Try to find specific elements
            try:
                # Look for availability status
                availability_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'available') or contains(text(), 'reservation')]")
                for element in availability_elements:
                    text = element.text.strip()
                    if text:
                        availability_info['availability_text'] += text + " | "
                        if 'no free spots' in text.lower():
                            availability_info['has_availability'] = False
                        elif 'available' in text.lower() and 'no free spots' not in text.lower():
                            availability_info['has_availability'] = True
                
                # Look for next available date
                next_available_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'next available') or contains(text(), 'Mon,') or contains(text(), 'Tue,') or contains(text(), 'Wed,') or contains(text(), 'Thu,') or contains(text(), 'Fri,') or contains(text(), 'Sat,') or contains(text(), 'Sun,')]")
                for element in next_available_elements:
                    text = element.text.strip()
                    if 'next available' in text.lower() or any(day in text for day in ['Mon,', 'Tue,', 'Wed,', 'Thu,', 'Fri,', 'Sat,', 'Sun,']):
                        availability_info['next_available'] = text
                        break
                
                # Look for operating hours
                hours_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '7:30am') or contains(text(), 'pm')]")
                for element in hours_elements:
                    text = element.text.strip()
                    if '7:30am' in text or 'pm' in text:
                        availability_info['operating_hours'] = text
                        break
                
            except Exception as e:
                print(f"⚠️  Error extracting specific elements: {e}")
            
            # Clean up the availability text
            if availability_info['availability_text']:
                availability_info['availability_text'] = availability_info['availability_text'].rstrip(' | ')
            
            return availability_info
            
        except Exception as e:
            print(f"❌ Error extracting availability info: {e}")
            return None
    
    def check_alice_marble(self):
        """Check Alice Marble tennis court availability"""
        url = "https://rec.us/alicemarble"
        return self.check_tennis_availability(url, "Alice Marble")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                # Check if there are any open windows/tabs
                if len(self.driver.window_handles) > 0:
                    self.driver.quit()
                    print("🔒 Browser closed")
                else:
                    print("🔒 Browser already closed")
            except Exception as e:
                print(f"⚠️  Error closing browser: {e}")
                # Force quit if there's an issue
                try:
                    self.driver.quit()
                except:
                    pass

def main():
    """Main function to run the availability checker"""
    print("🎾 Tennis Court Availability Checker")
    print("=" * 50)
    
    checker = TennisAvailabilityChecker(use_existing_session=True)
    
    try:
        # Set up the driver
        if not checker.setup_driver():
            return False
        
        # Check Alice Marble availability
        availability = checker.check_alice_marble()
        
        if availability:
            print(f"\n📊 Availability Results:")
            print(f"  Court: Alice Marble")
            print(f"  Has Availability: {'✅ Yes' if availability['has_availability'] else '❌ No'}")
            print(f"  Availability Text: {availability['availability_text']}")
            print(f"  Next Available: {availability['next_available']}")
            print(f"  Operating Hours: {availability['operating_hours']}")
            print(f"  Patterns Found: {', '.join(availability['raw_text_found'])}")
            
            # Results are already printed above, no need to save JSON files
        
        return True
        
    except Exception as e:
        print(f"❌ Error in main: {e}")
        return False
    
    finally:
        checker.close()

if __name__ == "__main__":
    main()

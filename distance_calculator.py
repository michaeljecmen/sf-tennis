#!/usr/bin/env python3
"""
Distance Calculator

Calculates biking distances from a given address to all tennis courts using web scraping.
Stores results in a JSON file for use by the main tennis availability checker.
"""

import json
import os
import time
import requests
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class DistanceCalculator:
    def __init__(self):
        self.driver = None
        self.court_distances_file = 'court_distances.json'
        
    def load_court_addresses(self, filename: str = 'court_addresses.json') -> List[Dict]:
        """Load court addresses from JSON file"""
        try:
            if not os.path.exists(filename):
                print(f"❌ Court addresses file not found: {filename}")
                print("💡 Run court_address_scraper.py first to get court addresses")
                return []
            
            with open(filename, 'r', encoding='utf-8') as f:
                court_addresses = json.load(f)
            
            print(f"📄 Loaded {len(court_addresses)} court addresses from {filename}")
            return court_addresses
            
        except Exception as e:
            print(f"❌ Error loading court addresses: {e}")
            return []
    
    def setup_driver(self):
        """Set up Firefox driver with optimized options (same as sf-tennis)"""
        if self.driver:
            return True
            
        firefox_options = Options()
        
        # Optimized preferences for speed
        firefox_options.set_preference("general.useragent.override", 
                                     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        firefox_options.binary_location = "/Applications/Firefox.app/Contents/MacOS/firefox"
        
        # Speed optimizations
        firefox_options.set_preference("permissions.default.image", 2)  # No images
        firefox_options.set_preference("browser.tabs.warnOnClose", False)
        firefox_options.set_preference("browser.tabs.warnOnCloseOtherTabs", False)
        firefox_options.set_preference("browser.shell.checkDefaultBrowser", False)
        firefox_options.set_preference("browser.startup.page", 0)
        firefox_options.set_preference("browser.startup.homepage", "about:blank")
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference("useAutomationExtension", False)
        
        # Additional speed optimizations
        firefox_options.set_preference("javascript.enabled", True)
        firefox_options.set_preference("dom.disable_beforeunload", True)
        firefox_options.set_preference("browser.cache.disk.enable", False)
        firefox_options.set_preference("browser.cache.memory.enable", False)
        firefox_options.set_preference("browser.cache.offline.enable", False)
        firefox_options.set_preference("network.http.use-cache", False)
        firefox_options.set_preference("media.autoplay.default", 5)  # Block autoplay
        firefox_options.set_preference("dom.push.enabled", False)
        firefox_options.set_preference("dom.serviceWorkers.enabled", False)
        
        # Try headless first
        try:
            firefox_options.add_argument("--headless")
            self.driver = webdriver.Firefox(options=firefox_options)
            return True
        except Exception:
            # Fallback to visible mode
            firefox_options = Options()
            firefox_options.set_preference("general.useragent.override", 
                                         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            firefox_options.binary_location = "/Applications/Firefox.app/Contents/MacOS/firefox"
            firefox_options.set_preference("permissions.default.image", 2)
            firefox_options.set_preference("browser.tabs.warnOnClose", False)
            firefox_options.set_preference("browser.tabs.warnOnCloseOtherTabs", False)
            firefox_options.set_preference("browser.shell.checkDefaultBrowser", False)
            firefox_options.set_preference("browser.startup.page", 0)
            firefox_options.set_preference("browser.startup.homepage", "about:blank")
            
            try:
                self.driver = webdriver.Firefox(options=firefox_options)
                self.driver.minimize_window()
                return True
            except Exception as e:
                print(f"❌ Error initializing Firefox: {e}")
                return False
    
    def calculate_distance(self, origin: str, destination: str) -> Optional[Dict]:
        """Calculate biking distance between two addresses using web scraping"""
        try:
            if not self.setup_driver():
                return None
            
            # Create Google Maps URL for biking directions
            origin_encoded = quote_plus(origin)
            destination_encoded = quote_plus(destination)
            maps_url = f"https://www.google.com/maps/dir/{origin_encoded}/{destination_encoded}/@bicycling"
            
            print(f"  🌐 Scraping: {destination[:50]}...")
            self.driver.get(maps_url)
            
            # Wait for the page to load
            wait = WebDriverWait(self.driver, 10)
            
            # Look for distance and duration information
            try:
                # Wait for the directions panel to load
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-value='Directions']")))
                time.sleep(2)  # Give it a moment to fully load
                
                # Look for distance and time elements
                distance_selectors = [
                    "span[jsaction*='distance']",
                    "[data-value*='mi']",
                    "[data-value*='km']",
                    ".section-directions-trip-distance",
                    ".section-directions-trip-duration"
                ]
                
                duration_selectors = [
                    "span[jsaction*='duration']",
                    "[data-value*='min']",
                    "[data-value*='hour']",
                    ".section-directions-trip-duration"
                ]
                
                distance_text = None
                duration_text = None
                
                # Try to find distance
                for selector in distance_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            if text and ('mi' in text or 'km' in text or 'mile' in text):
                                distance_text = text
                                break
                        if distance_text:
                            break
                    except:
                        continue
                
                # Try to find duration
                for selector in duration_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            if text and ('min' in text or 'hour' in text):
                                duration_text = text
                                break
                        if duration_text:
                            break
                    except:
                        continue
                
                # If we didn't find specific elements, try parsing the page source
                if not distance_text or not duration_text:
                    page_source = self.driver.page_source
                    
                    # Look for distance patterns
                    if not distance_text:
                        distance_patterns = [
                            r'(\d+\.?\d*)\s*(mi|miles?|km|kilometers?)',
                            r'(\d+\.?\d*)\s*(mile|miles)',
                        ]
                        for pattern in distance_patterns:
                            match = re.search(pattern, page_source, re.IGNORECASE)
                            if match:
                                distance_text = f"{match.group(1)} {match.group(2)}"
                                break
                    
                    # Look for duration patterns
                    if not duration_text:
                        duration_patterns = [
                            r'(\d+)\s*(min|minutes?)',
                            r'(\d+)\s*(hour|hours?)',
                            r'(\d+)\s*(hr|hrs)',
                        ]
                        for pattern in duration_patterns:
                            match = re.search(pattern, page_source, re.IGNORECASE)
                            if match:
                                duration_text = f"{match.group(1)} {match.group(2)}"
                                break
                
                if not distance_text or not duration_text:
                    print(f"  ⚠️  Could not find distance/time for {destination}")
                    return None
                
                # Parse duration to seconds
                duration_seconds = self.parse_duration_to_seconds(duration_text)
                duration_minutes = round(duration_seconds / 60, 1) if duration_seconds else 0
                
                return {
                    'distance_text': distance_text,
                    'duration_text': duration_text,
                    'distance_meters': self.parse_distance_to_meters(distance_text),
                    'duration_seconds': duration_seconds,
                    'duration_minutes': duration_minutes
                }
                
            except TimeoutException:
                print(f"  ⚠️  Timeout loading directions for {destination}")
                return None
            except Exception as e:
                print(f"  ⚠️  Error parsing directions for {destination}: {e}")
                return None
                
        except Exception as e:
            print(f"❌ Error calculating distance to {destination}: {e}")
            return None
    
    def parse_duration_to_seconds(self, duration_text: str) -> int:
        """Parse duration text to seconds"""
        try:
            duration_text = duration_text.lower().strip()
            
            # Handle minutes
            if 'min' in duration_text:
                minutes = re.search(r'(\d+)', duration_text)
                if minutes:
                    return int(minutes.group(1)) * 60
            
            # Handle hours
            if 'hour' in duration_text or 'hr' in duration_text:
                hours = re.search(r'(\d+)', duration_text)
                if hours:
                    return int(hours.group(1)) * 3600
            
            # Handle hours and minutes (e.g., "1 hour 30 min")
            hour_match = re.search(r'(\d+)\s*hour', duration_text)
            min_match = re.search(r'(\d+)\s*min', duration_text)
            
            if hour_match and min_match:
                hours = int(hour_match.group(1))
                minutes = int(min_match.group(1))
                return hours * 3600 + minutes * 60
            
            return 0
        except:
            return 0
    
    def parse_distance_to_meters(self, distance_text: str) -> int:
        """Parse distance text to meters"""
        try:
            distance_text = distance_text.lower().strip()
            
            # Extract number
            number_match = re.search(r'(\d+\.?\d*)', distance_text)
            if not number_match:
                return 0
            
            distance = float(number_match.group(1))
            
            # Convert to meters based on unit
            if 'mi' in distance_text or 'mile' in distance_text:
                return int(distance * 1609.34)  # miles to meters
            elif 'km' in distance_text or 'kilometer' in distance_text:
                return int(distance * 1000)  # km to meters
            else:
                return int(distance * 1609.34)  # assume miles if unclear
            
        except:
            return 0
    
    def calculate_all_distances(self, origin_address: str, court_addresses: List[Dict]) -> List[Dict]:
        """Calculate distances from origin to all courts"""
        print(f"🚴 Calculating biking distances from: {origin_address}")
        print(f"📍 To {len(court_addresses)} tennis courts")
        print("=" * 60)
        
        results = []
        
        try:
            for i, court in enumerate(court_addresses, 1):
                court_name = court['name']
                court_address = court.get('address')
                
                if not court_address:
                    print(f"⚠️  [{i}/{len(court_addresses)}] {court_name}: No address available")
                    results.append({
                        'court_name': court_name,
                        'court_url': court['url'],
                        'court_address': None,
                        'distance_info': None,
                        'error': 'No address available'
                    })
                    continue
                
                print(f"🚴 [{i}/{len(court_addresses)}] {court_name}...")
                
                distance_info = self.calculate_distance(origin_address, court_address)
                
                if distance_info:
                    print(f"  ✅ {distance_info['duration_text']} ({distance_info['distance_text']})")
                else:
                    print(f"  ❌ Failed to calculate distance")
                
                results.append({
                    'court_name': court_name,
                    'court_url': court['url'],
                    'court_address': court_address,
                    'distance_info': distance_info,
                    'error': None if distance_info else 'Distance calculation failed'
                })
                
                # Small delay between requests to be respectful
                time.sleep(1)  # 1 second delay between requests
            
        finally:
            # Clean up the driver
            if self.driver:
                try:
                    self.driver.quit()
                    print("🔒 Browser closed")
                except:
                    pass
        
        return results
    
    def save_distances(self, origin_address: str, results: List[Dict]) -> bool:
        """Save distance results to JSON file"""
        try:
            # Filter out courts with errors for the main data
            successful_results = [r for r in results if r['distance_info']]
            failed_results = [r for r in results if not r['distance_info']]
            
            # Sort by duration (closest first)
            successful_results.sort(key=lambda x: x['distance_info']['duration_seconds'])
            
            distance_data = {
                'origin_address': origin_address,
                'calculated_at': datetime.now().isoformat(),
                'total_courts': len(results),
                'successful_calculations': len(successful_results),
                'failed_calculations': len(failed_results),
                'courts_by_distance': successful_results,
                'failed_courts': failed_results
            }
            
            with open(self.court_distances_file, 'w', encoding='utf-8') as f:
                json.dump(distance_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Saved distance data to {self.court_distances_file}")
            print(f"📊 Successfully calculated: {len(successful_results)} courts")
            print(f"❌ Failed calculations: {len(failed_results)} courts")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving distances: {e}")
            return False
    
    def load_existing_distances(self) -> Optional[Dict]:
        """Load existing distance data"""
        try:
            if not os.path.exists(self.court_distances_file):
                return None
            
            with open(self.court_distances_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"⚠️  Error loading existing distances: {e}")
            return None
    
    def show_summary(self, results: List[Dict]):
        """Show a summary of the closest courts"""
        successful = [r for r in results if r['distance_info']]
        if not successful:
            print("❌ No successful distance calculations")
            return
        
        print(f"\n🏆 CLOSEST TENNIS COURTS (by biking time):")
        print("=" * 60)
        
        for i, court in enumerate(successful[:10], 1):  # Show top 10
            name = court['court_name']
            duration = court['distance_info']['duration_text']
            distance = court['distance_info']['distance_text']
            address = court['court_address']
            
            print(f"{i:2d}. {name}")
            print(f"    ⏱️  {duration} ({distance})")
            print(f"    📍 {address}")
            print()

def main():
    """Main function to calculate distances"""
    import sys
    
    print("🚴 Tennis Court Distance Calculator (Web Scraping)")
    print("=" * 60)
    
    # Get origin address from command line
    if len(sys.argv) > 1:
        origin_address = ' '.join(sys.argv[1:])
    else:
        print("❌ Address is required!")
        print("💡 Usage: python distance_calculator.py 'Your Address Here'")
        return
    
    print("🌐 Using web scraping (completely free!)")
    print("⏱️  This may take a few minutes as we scrape each court...")
    
    try:
        calculator = DistanceCalculator()
        
        # Load court addresses
        court_addresses = calculator.load_court_addresses()
        if not court_addresses:
            return
        
        # Calculate distances
        results = calculator.calculate_all_distances(origin_address, court_addresses)
        
        # Save results
        calculator.save_distances(origin_address, results)
        
        # Show summary
        calculator.show_summary(results)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

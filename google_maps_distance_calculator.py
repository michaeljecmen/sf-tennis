#!/usr/bin/env python3
"""
Google Maps Distance Calculator

Uses Google Maps interaction to get accurate biking distances:
1. Find Google Maps link on court page
2. Click it to open Google Maps
3. Click "Directions" 
4. Enter user's address in "Your location"
5. Get biking time
"""

import json
import os
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor, as_completed

class GoogleMapsDistanceCalculator:
    def __init__(self):
        self.driver = None
        self.court_distances_file = 'court_distances.json'
        
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
        
        # Try headless first for production
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
    
    def get_court_urls(self) -> List[Dict]:
        """Get court URLs by scraping the main SF Rec & Park page"""
        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            
            print("🔍 Scraping court URLs from SF Rec & Park...")
            base_url = "https://sfrecpark.org/1446/Reservable-Tennis-Courts"
            
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            links = soup.find_all('a', href=True)
            urls = []
            
            for link in links:
                url = urljoin(base_url, link['href'])
                text = link.get_text(strip=True)
                urls.append({'url': url, 'text': text})
            
            # Filter for tennis courts
            tennis_keywords = ['tennis', 'court']
            excluded_url = "https://sfrecpark.org/1446/Reservable-Tennis-Courts"
            
            tennis_urls = []
            for url_data in urls:
                url = url_data['url'].lower()
                text = url_data['text'].lower()
                if url_data['url'] == excluded_url:
                    continue
                if any(keyword in url or keyword in text for keyword in tennis_keywords):
                    tennis_urls.append(url_data)
            
            # Filter for rec.us URLs and deduplicate by URL
            unique_courts = {}
            for court in tennis_urls:
                url = court['url']
                text = court['text']
                if 'rec.us' in url and any(keyword in text.lower() for keyword in ['tennis', 'court']):
                    if url not in unique_courts:
                        unique_courts[url] = {
                            'name': text,
                            'url': url
                        }
                    else:
                        # Keep the longer name if available
                        existing = unique_courts[url]
                        if len(text) > len(existing['name']):
                            existing['name'] = text
            
            court_urls = list(unique_courts.values())
            print(f"📄 Found {len(court_urls)} court URLs")
            return court_urls
            
        except Exception as e:
            print(f"❌ Error loading court URLs: {e}")
            return []
    
    def get_google_maps_link(self, court_url: str) -> Optional[str]:
        """Get Google Maps link from court page"""
        try:
            if not self.setup_driver():
                return None
                
            print(f"  🌐 Loading court page: {court_url}")
            self.driver.get(court_url)
            time.sleep(3)  # Wait for page load
            
            # Look for Google Maps link
            maps_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'google.com/maps')]")
            
            if maps_links:
                maps_url = maps_links[0].get_attribute('href')
                print(f"  📍 Found Google Maps link: {maps_url[:50]}...")
                return maps_url
            else:
                print(f"  ⚠️  No Google Maps link found")
                return None
                
        except Exception as e:
            print(f"  ❌ Error getting Google Maps link: {e}")
            return None
    
    def get_biking_time_from_maps(self, maps_url: str, origin_address: str) -> Optional[Dict]:
        """Get biking time by interacting with Google Maps step by step"""
        try:
            print(f"  🗺️  Opening Google Maps...")
            self.driver.get(maps_url)
            time.sleep(3)  # Wait for maps to load
            
            # Click "Directions" button
            print(f"  🧭 Clicking Directions...")
            directions_selectors = [
                "//button[contains(text(), 'Directions')]",
                "//button[contains(@aria-label, 'Directions')]",
                "//*[contains(text(), 'Directions')]",
                "//button[contains(@data-value, 'Directions')]"
            ]
            
            directions_clicked = False
            for selector in directions_selectors:
                try:
                    directions_btn = self.driver.find_element(By.XPATH, selector)
                    if directions_btn.is_displayed() and directions_btn.is_enabled():
                        directions_btn.click()
                        directions_clicked = True
                        print(f"  ✅ Clicked Directions button")
                        break
                except:
                    continue
            
            if not directions_clicked:
                print(f"  ⚠️  Could not find Directions button")
                return None
            
            time.sleep(2)  # Wait for directions panel
            
            # Find and fill "Your location" field
            print(f"  📍 Entering origin address: {origin_address}")
            origin_selectors = [
                "//input[@placeholder='Choose starting point, or click on the map...']",
                "//input[contains(@placeholder, 'starting point')]",
                "//input[contains(@placeholder, 'Your location')]",
                "//input[@data-value='Directions']",
                "//input[contains(@aria-label, 'starting point')]",
                "//input[contains(@aria-label, 'Choose starting point')]",
                "//input[contains(@placeholder, 'Choose starting point')]"
            ]
            
            origin_field = None
            for selector in origin_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            origin_field = element
                            print(f"  ✅ Found origin field with selector: {selector}")
                            break
                    if origin_field:
                        break
                except:
                    continue
            
            if not origin_field:
                print(f"  ⚠️  Could not find origin input field")
                return None
            
            # Clear and enter address
            origin_field.clear()
            time.sleep(0.5)
            origin_field.send_keys(origin_address)
            time.sleep(2)  # Wait for address to be typed
            
            # Look for and click the search button (magnifying glass)
            print(f"  🔍 Looking for search button...")
            search_selectors = [
                "//button[contains(@aria-label, 'Search')]",
                "//button[contains(@aria-label, 'search')]",
                "//button[contains(@title, 'Search')]",
                "//button[contains(@title, 'search')]",
                "//button[contains(@class, 'search')]",
                "//button[contains(@class, 'Search')]",
                "//input[@type='submit']",
                "//button[@type='submit']"
            ]
            
            search_clicked = False
            for selector in search_selectors:
                try:
                    search_buttons = self.driver.find_elements(By.XPATH, selector)
                    for button in search_buttons:
                        if button.is_displayed() and button.is_enabled():
                            button.click()
                            print(f"  ✅ Clicked search button with selector: {selector}")
                            search_clicked = True
                            time.sleep(3)  # Wait for search to process
                            break
                    if search_clicked:
                        break
                except Exception as e:
                    print(f"  ⚠️  Error with search selector {selector}: {e}")
                    continue
            
            if not search_clicked:
                print(f"  ⚠️  No search button found, trying Enter key")
                origin_field.send_keys("\n")
                time.sleep(3)
            
            # Check if address was processed by looking at the field value
            field_value = origin_field.get_attribute('value')
            print(f"  🔍 Field value after processing: '{field_value}'")
            
            # Wait a bit more for directions to calculate
            time.sleep(3)
            
            # Debug: print page title and URL
            print(f"  🔍 Page title: {self.driver.title}")
            print(f"  🔍 Current URL: {self.driver.current_url}")
            
            # Check if the URL now contains our address
            if '1892+Market+St' in self.driver.current_url:
                print(f"  ✅ Address successfully processed in URL")
            else:
                print(f"  ⚠️  Address not found in URL")
            
            # Select biking mode
            print(f"  🚴 Selecting biking mode...")
            time.sleep(2)  # Wait longer for the page to fully load
            
            # Dump HTML for debugging
            print(f"  🔍 Dumping HTML for debugging...")
            page_source = self.driver.page_source
            with open('debug_maps_page.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"  💾 Saved HTML to debug_maps_page.html")
            
            bike_selectors = [
                # Target the specific cycling button from the HTML
                "//button[@data-travel_mode='1' and contains(@aria-label, 'Cycling')]",
                "//div[@data-travel_mode='1']//button[contains(@aria-label, 'Cycling')]",
                "//button[contains(@aria-label, 'Cycling')]",
                "//button[contains(@aria-label, 'Bicycling')]",
                "//button[contains(@aria-label, 'bike')]",
                "//button[contains(text(), 'Cycling')]",
                "//button[contains(text(), 'Bicycling')]",
                "//button[contains(text(), 'bike')]",
                "//*[contains(@aria-label, 'Cycling')]",
                "//*[contains(@aria-label, 'Bicycling')]",
                "//*[contains(@aria-label, 'bike')]"
            ]
            
            bike_selected = False
            for selector in bike_selectors:
                try:
                    bike_buttons = self.driver.find_elements(By.XPATH, selector)
                    for bike_btn in bike_buttons:
                        if bike_btn.is_displayed() and bike_btn.is_enabled():
                            bike_btn.click()
                            print(f"  ✅ Selected biking mode with selector: {selector}")
                            bike_selected = True
                            time.sleep(5)  # Wait longer for mode change
                            break
                    if bike_selected:
                        break
                except Exception as e:
                    print(f"  ⚠️  Error with bike selector {selector}: {e}")
                    continue
            
            if not bike_selected:
                print(f"  ⚠️  Could not find biking mode button")
                # Debug: print all buttons to see what's available
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                print(f"  🔍 Found {len(all_buttons)} buttons on page")
                for i, btn in enumerate(all_buttons[:20]):  # Show first 20
                    aria_label = btn.get_attribute('aria-label') or 'No aria-label'
                    text = btn.text.strip()
                    class_name = btn.get_attribute('class') or 'No class'
                    if any(word in aria_label.lower() for word in ['bike', 'bicycling', 'travel', 'mode', 'drive', 'walk', 'transit']) or any(word in text.lower() for word in ['bike', 'bicycling', 'travel', 'mode', 'drive', 'walk', 'transit']):
                        print(f"    Button {i}: aria-label='{aria_label}', text='{text}', class='{class_name}'")
                
                # Also look for travel mode container
                travel_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'travel-mode') or contains(@class, 'travel') or contains(@class, 'mode')]")
                print(f"  🔍 Found {len(travel_containers)} travel mode containers")
                for i, container in enumerate(travel_containers[:5]):
                    text = container.text.strip()
                    class_name = container.get_attribute('class')
                    print(f"    Container {i}: class='{class_name}', text='{text[:100]}...'")
            
            # Look for biking time
            print(f"  🚴 Looking for biking time...")
            
            # Debug: print all text elements containing 'min'
            print(f"  🔍 Debug: Looking for all elements with 'min'...")
            min_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'min')]")
            for i, element in enumerate(min_elements[:10]):  # Show first 10
                text = element.text.strip()
                if text:  # Only show non-empty elements
                    print(f"    Element {i}: '{text}'")
            
            # Look for time elements - try various selectors
            time_selectors = [
                "//*[contains(text(), 'min') and contains(text(), 'bike')]",
                "//*[contains(text(), 'min') and contains(@class, 'bike')]",
                "//*[contains(text(), 'min')]//*[contains(text(), 'bike')]",
                "//*[contains(@aria-label, 'bike')]//*[contains(text(), 'min')]",
                "//*[contains(text(), 'bike')]//*[contains(text(), 'min')]",
                # Look for cycling-specific times (24 min from the HTML)
                "//div[contains(text(), '24 min')]",
                "//*[contains(text(), '24 min')]",
                # Look for any time that's not 14 min (driving time)
                "//*[contains(text(), 'min') and not(contains(text(), '14 min'))]",
                "//*[contains(text(), 'min')]"  # Just look for any time
            ]
            
            for selector in time_selectors:
                try:
                    time_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in time_elements:
                        text = element.text.strip()
                        if 'min' in text:
                            # Extract time
                            time_match = re.search(r'(\d+)\s*min', text)
                            if time_match:
                                minutes = int(time_match.group(1))
                                print(f"  ✅ Found time: {minutes} minutes (text: '{text}')")
                                return {
                                    'duration_text': f"{minutes} min",
                                    'duration_seconds': minutes * 60,
                                    'duration_minutes': minutes,
                                    'distance_text': 'Unknown',  # We don't need distance for sorting
                                    'distance_meters': 0
                                }
                except:
                    continue
            
            print(f"  ⚠️  Could not find biking time")
            return None
            
        except Exception as e:
            print(f"  ❌ Error getting biking time: {e}")
            return None
    
    def calculate_single_court_distance(self, court_data: Dict, origin_address: str) -> Dict:
        """Calculate distance for a single court"""
        court_name = court_data['name']
        court_url = court_data['url']
        
        # Create a new calculator instance for this thread
        calculator = GoogleMapsDistanceCalculator()
        
        try:
            if not calculator.setup_driver():
                return {
                    'court_name': court_name,
                    'court_url': court_url,
                    'distance_info': None,
                    'error': 'Failed to initialize driver'
                }
            
            # Get Google Maps link
            maps_url = calculator.get_google_maps_link(court_url)
            if not maps_url:
                return {
                    'court_name': court_name,
                    'court_url': court_url,
                    'distance_info': None,
                    'error': 'No Google Maps link found'
                }
            
            # Get biking time
            distance_info = calculator.get_biking_time_from_maps(maps_url, origin_address)
            
            return {
                'court_name': court_name,
                'court_url': court_url,
                'distance_info': distance_info,
                'error': None if distance_info else 'Could not get biking time'
            }
                
        except Exception as e:
            return {
                'court_name': court_name,
                'court_url': court_url,
                'distance_info': None,
                'error': str(e)
            }
        finally:
            if calculator.driver:
                try:
                    calculator.driver.quit()
                except:
                    pass
    
    def calculate_all_distances(self, origin_address: str, court_urls: List[Dict], max_workers=4) -> List[Dict]:
        """Calculate distances from origin to all courts in parallel"""
        print(f"🚴 Calculating biking distances from: {origin_address}")
        print(f"📍 To {len(court_urls)} tennis courts")
        print("=" * 60)
        
        # Auto-optimize worker count (fewer workers for Google Maps interaction)
        if max_workers == 4:  # Default
            if len(court_urls) < 10:
                max_workers = min(2, len(court_urls))
            elif len(court_urls) < 20:
                max_workers = min(3, len(court_urls))
            else:
                max_workers = min(4, len(court_urls))
        
        start_time = time.time()
        results = []
        completed = 0
        total = len(court_urls)
        
        # Show initial progress bar
        print(f"⏳ calculating distances for {total} courts...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_court = {
                executor.submit(self.calculate_single_court_distance, court, origin_address): court 
                for court in court_urls
            }
            
            for future in as_completed(future_to_court):
                result = future.result()
                results.append(result)
                completed += 1
                
                # Update progress bar every completion
                elapsed = time.time() - start_time
                progress = completed / total
                bar_length = 40
                filled_length = int(bar_length * progress)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                # Calculate ETA
                if completed > 0:
                    eta = (elapsed / completed) * (total - completed)
                    eta_str = f"ETA: {eta:.0f}s" if eta > 0 else "ETA: --"
                else:
                    eta_str = "ETA: --"
                
                print(f"\r⏳ [{bar}] {completed}/{total} ({progress:.1%}) | {elapsed:.0f}s | {eta_str}", end='', flush=True)
        
        elapsed = time.time() - start_time
        print(f"\r✅ completed {total} courts in {elapsed:.1f}s ({total/elapsed:.1f} courts/sec)")
        
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
            
            print(f"{i:2d}. {name}")
            print(f"    ⏱️  {duration}")
            print()

def main():
    """Main function to calculate distances"""
    import sys
    
    print("🚴 Google Maps Distance Calculator")
    print("=" * 60)
    
    # Get origin address from command line
    if len(sys.argv) > 1:
        origin_address = ' '.join(sys.argv[1:])
    else:
        print("❌ Address is required!")
        print("💡 Usage: python google_maps_distance_calculator.py 'Your Address Here'")
        return
    
    print("🌐 Using Google Maps interaction (completely free!)")
    print("⏱️  This may take a few minutes as we interact with Google Maps...")
    
    try:
        calculator = GoogleMapsDistanceCalculator()
        
        # Load court URLs
        court_urls = calculator.get_court_urls()
        if not court_urls:
            return
        
        # Calculate distances
        results = calculator.calculate_all_distances(origin_address, court_urls)
        
        # Save results
        calculator.save_distances(origin_address, results)
        
        # Show summary
        calculator.show_summary(results)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

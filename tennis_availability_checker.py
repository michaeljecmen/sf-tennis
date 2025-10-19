#!/usr/bin/env python3
"""
Tennis Court Availability Checker

Automates Firefox to check tennis court availability on SF Rec & Park pages.
"""

import time
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
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
        
        # Minimize focus stealing
        firefox_options.set_preference("browser.tabs.warnOnClose", False)
        firefox_options.set_preference("browser.tabs.warnOnCloseOtherTabs", False)
        firefox_options.set_preference("browser.shell.checkDefaultBrowser", False)
        firefox_options.set_preference("browser.startup.page", 0)  # Don't load any page on startup
        firefox_options.set_preference("browser.startup.homepage", "about:blank")
        
        # Try to run in headless mode first (no visible window)
        # If that doesn't work, we'll fall back to visible mode
        try:
            print("🔄 Attempting to run in headless mode (no visible window)...")
            firefox_options.add_argument("--headless")
            self.driver = webdriver.Firefox(options=firefox_options)
            print("✅ Firefox driver initialized in headless mode")
            return True
        except Exception as e:
            print(f"⚠️  Headless mode failed: {e}")
            print("🔄 Falling back to visible mode...")
            # Remove headless argument and try again
            firefox_options = Options()
            firefox_options.set_preference("general.useragent.override", 
                                         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            firefox_options.binary_location = "/Applications/Firefox.app/Contents/MacOS/firefox"
            firefox_options.set_preference("permissions.default.image", 2)
            firefox_options.set_preference("browser.tabs.warnOnClose", False)
            firefox_options.set_preference("browser.tabs.warnOnCloseOtherTabs", False)
            firefox_options.set_preference("browser.shell.checkDefaultBrowser", False)
            firefox_options.set_preference("browser.startup.page", 0)
            firefox_options.set_preference("browser.startup.homepage", "about:blank")
        
        try:
            print("🔄 Starting new Firefox session...")
            self.driver = webdriver.Firefox(options=firefox_options)
            print("✅ Firefox driver initialized successfully")
            
            # Try to minimize the window to reduce focus stealing
            try:
                self.driver.minimize_window()
                print("📱 Browser window minimized")
            except Exception as e:
                print(f"⚠️  Could not minimize window: {e}")
            
            return True
        except Exception as e:
            print(f"❌ Error initializing Firefox driver: {e}")
            return False
    
    def check_tennis_availability(self, url, court_name="Tennis Court", date_input=None):
        """Check availability for a specific tennis court page on a specific date"""
        if not self.driver:
            print("❌ Driver not initialized")
            return None
        
        # Parse the date input if provided
        target_date = None
        if date_input:
            target_date = self.parse_date_input(date_input)
            if target_date:
                print(f"📅 Target date: {target_date.strftime('%A, %B %d, %Y')}")
            else:
                print(f"⚠️  Could not parse date: '{date_input}' - using next available date")
        
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
            
            # Try to click on the specific date or next available date
            self.click_specific_date(target_date)
            
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
    
    def click_specific_date(self, target_date=None):
        """Try to click on a specific date to get times for that date"""
        try:
            if target_date:
                print(f"🔍 Looking for specific date: {target_date.strftime('%A, %B %d, %Y')}")
            else:
                print("🔍 Looking for next available date to click...")
            
            # First, try to find and click the date picker to open it
            date_picker_selectors = [
                "//*[contains(@class, 'react-datepicker-wrapper')]",
                "//*[contains(@class, 'date') and contains(@class, 'picker')]",
                "//*[contains(@class, 'calendar')]",
                "//*[contains(@class, 'picker')]",
                "//input[@type='date']"
            ]
            
            # Try to open the date picker first
            for selector in date_picker_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"🔍 Checking date picker selector '{selector}': found {len(elements)} elements")
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            print(f"📅 Found date picker: {element.text[:50]}...")
                            print(f"   Element tag: {element.tag_name}, classes: {element.get_attribute('class')}")
                            element.click()
                            print("✅ Clicked on date picker")
                            time.sleep(2)  # Wait for calendar to open
                            
                            # Now look for specific date elements within the opened calendar
                            if target_date:
                                # Look for the specific date
                                day_number = str(target_date.day)
                                month_name = target_date.strftime('%b').lower()
                                day_name = target_date.strftime('%a').lower()
                                
                                date_selectors = [
                                    f"//*[contains(@class, 'react-datepicker__day') and contains(text(), '{day_number}')]",
                                    f"//*[contains(@class, 'day') and contains(text(), '{day_number}')]",
                                    f"//*[contains(text(), '{day_number}') and not(contains(text(), 'St'))]"
                                ]
                            else:
                                # Look for next available date (original behavior)
                                date_selectors = [
                                    "//*[contains(@class, 'react-datepicker__day') and contains(text(), '20')]",  # October 20
                                    "//*[contains(@class, 'react-datepicker__day')]",  # Any calendar day
                                    "//*[contains(@class, 'day') and contains(@class, 'available')]",  # Available days
                                    "//*[contains(@class, 'day') and not(contains(@class, 'disabled'))]",  # Non-disabled days
                                    "//*[contains(@class, 'day')]",
                                    "//*[contains(text(), '20') and not(contains(text(), 'St'))]",  # 20 but not "St"
                                    "//*[contains(text(), 'Mon') and not(contains(text(), 'Marble'))]"  # Mon but not "Marble"
                                ]
                            
                            for date_selector in date_selectors:
                                try:
                                    date_elements = self.driver.find_elements(By.XPATH, date_selector)
                                    print(f"🔍 Looking for date '{date_selector}': found {len(date_elements)} elements")
                                    for date_element in date_elements:
                                        if date_element.is_displayed() and date_element.is_enabled():
                                            text = date_element.text.strip()
                                            if target_date:
                                                # For specific date, look for the day number
                                                if day_number in text and len(text) <= 2:
                                                    print(f"📅 Found target date element: {text}")
                                                    date_element.click()
                                                    print(f"✅ Clicked on {target_date.strftime('%A, %B %d')}")
                                                    time.sleep(3)  # Wait for times to load
                                                    return True
                                            else:
                                                # Original behavior for next available
                                                if '20' in text or 'Mon' in text:
                                                    print(f"📅 Found date element: {text}")
                                                    date_element.click()
                                                    print("✅ Clicked on specific date")
                                                    time.sleep(3)  # Wait for times to load
                                                    return True
                                except Exception as e:
                                    continue
                            
                            return True  # Even if we can't find specific date, we opened the picker
                except Exception as e:
                    print(f"⚠️  Error with date picker selector '{selector}': {e}")
                    continue
            
            print("⚠️  No clickable date picker found")
            return False
            
        except Exception as e:
            print(f"⚠️  Error clicking date: {e}")
            return False
    
    def parse_date_input(self, date_input):
        """Parse natural language date input into a datetime object"""
        if not date_input:
            return None
            
        date_input = date_input.lower().strip()
        today = datetime.now()
        
        # Handle "tomorrow"
        if date_input in ['tomorrow', 'tom']:
            return today + timedelta(days=1)
        
        # Handle "today"
        if date_input in ['today', 'now']:
            return today
        
        # Handle day of week (this week or next week)
        days_of_week = {
            'monday': 0, 'mon': 0, 'm': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1, 't': 1,
            'wednesday': 2, 'wed': 2, 'w': 2,
            'thursday': 3, 'thu': 3, 'thurs': 3, 'th': 3,
            'friday': 4, 'fri': 4, 'f': 4,
            'saturday': 5, 'sat': 5, 's': 5,
            'sunday': 6, 'sun': 6, 'su': 6
        }
        
        # Check for "next [day]" pattern
        if date_input.startswith('next '):
            day_name = date_input[5:].strip()
            if day_name in days_of_week:
                target_day = days_of_week[day_name]
                days_ahead = target_day - today.weekday()
                if days_ahead <= 0:  # Target day already passed this week
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
        
        # Check for just day name (this week)
        if date_input in days_of_week:
            target_day = days_of_week[date_input]
            days_ahead = target_day - today.weekday()
            if days_ahead < 0:  # Day already passed this week
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        
        # Handle "Oct 23", "October 23", "10/23", "10-23" patterns
        month_patterns = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }
        
        # Try to parse month/day patterns
        for month_name, month_num in month_patterns.items():
            if month_name in date_input:
                # Extract day number
                day_match = re.search(r'\b(\d{1,2})\b', date_input)
                if day_match:
                    day = int(day_match.group(1))
                    year = today.year
                    # If the date is in the past, assume next year
                    try:
                        target_date = datetime(year, month_num, day)
                        if target_date < today:
                            target_date = datetime(year + 1, month_num, day)
                        return target_date
                    except ValueError:
                        continue
        
        # Handle numeric patterns like "10/23", "10-23", "10.23"
        numeric_patterns = [
            r'(\d{1,2})[/\-\.](\d{1,2})',  # MM/DD or MM-DD
            r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})'  # MM/DD/YY or MM/DD/YYYY
        ]
        
        for pattern in numeric_patterns:
            match = re.search(pattern, date_input)
            if match:
                groups = match.groups()
                if len(groups) == 2:  # MM/DD
                    month, day = int(groups[0]), int(groups[1])
                    year = today.year
                    try:
                        target_date = datetime(year, month, day)
                        if target_date < today:
                            target_date = datetime(year + 1, month, day)
                        return target_date
                    except ValueError:
                        continue
                elif len(groups) == 3:  # MM/DD/YY or MM/DD/YYYY
                    month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    if year < 100:  # Two digit year
                        year += 2000 if year < 50 else 1900
                    try:
                        return datetime(year, month, day)
                    except ValueError:
                        continue
        
        # Handle relative days like "in 3 days", "3 days from now"
        relative_match = re.search(r'(\d+)\s*days?\s*(?:from now|ahead|later)?', date_input)
        if relative_match:
            days = int(relative_match.group(1))
            return today + timedelta(days=days)
        
        return None
    
    def find_duration_for_time_element(self, time_element):
        """Find duration information near a time element"""
        try:
            # Look for duration in the same element or nearby elements
            # Check the element's text for numbers that could be duration
            element_text = time_element.text.strip()
            
            # Look for numbers in the element text (like "10:00 AM 60")
            import re
            numbers = re.findall(r'\b(\d+)\b', element_text)
            for num in numbers:
                if 30 <= int(num) <= 180:  # Reasonable duration range (30-180 minutes)
                    return int(num)
            
            # Look in the parent element
            parent = time_element.find_element(By.XPATH, "..")
            parent_text = parent.text.strip()
            numbers = re.findall(r'\b(\d+)\b', parent_text)
            for num in numbers:
                if 30 <= int(num) <= 180:
                    return int(num)
            
            # Look in sibling elements
            try:
                siblings = time_element.find_elements(By.XPATH, "following-sibling::* | preceding-sibling::*")
                for sibling in siblings:
                    sibling_text = sibling.text.strip()
                    if sibling_text and len(sibling_text) < 10:  # Short text likely to be duration
                        numbers = re.findall(r'\b(\d+)\b', sibling_text)
                        for num in numbers:
                            if 30 <= int(num) <= 180:
                                return int(num)
            except:
                pass
            
            # Look for elements with duration-related classes
            duration_selectors = [
                ".//*[contains(@class, 'duration')]",
                ".//*[contains(@class, 'minutes')]",
                ".//*[contains(@class, 'length')]",
                ".//*[contains(@class, 'time-length')]"
            ]
            
            for selector in duration_selectors:
                try:
                    duration_elements = time_element.find_elements(By.XPATH, selector)
                    for duration_element in duration_elements:
                        duration_text = duration_element.text.strip()
                        numbers = re.findall(r'\b(\d+)\b', duration_text)
                        for num in numbers:
                            if 30 <= int(num) <= 180:
                                return int(num)
                except:
                    continue
            
            return None
            
        except Exception as e:
            print(f"⚠️  Error finding duration: {e}")
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
                'available_times': [],
                'time_slots_with_duration': [],
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
                
                # Look for specific time slots (after clicking on date)
                time_selectors = [
                    "//*[contains(@class, 'time')]",
                    "//*[contains(@class, 'slot')]", 
                    "//*[contains(@class, 'hour')]",
                    "//*[contains(@class, 'booking')]",
                    "//*[contains(@class, 'reservation')]",
                    "//*[contains(text(), 'AM') or contains(text(), 'PM')]",
                    "//button[contains(text(), 'AM') or contains(text(), 'PM') or contains(text(), ':')]",
                    "//*[contains(@class, 'react-datepicker__time')]",
                    "//*[contains(@class, 'time-picker')]",
                    "//*[contains(@class, 'time-slot')]"
                ]
                
                for selector in time_selectors:
                    try:
                        time_elements = self.driver.find_elements(By.XPATH, selector)
                        print(f"🔍 Looking for times with selector '{selector}': found {len(time_elements)} elements")
                        for element in time_elements:
                            text = element.text.strip()
                            # Look for time patterns like "8:00 AM", "2:30 PM", etc.
                            if any(pattern in text for pattern in ['AM', 'PM', ':', 'am', 'pm']):
                                if len(text) < 30 and len(text) > 2:  # Avoid long text blocks but include short times
                                    print(f"⏰ Found time element: {text}")
                                    availability_info['available_times'].append(text)
                                    
                                    # Try to find duration information near this time element
                                    duration = self.find_duration_for_time_element(element)
                                    if duration:
                                        time_slot = {
                                            'time': text,
                                            'duration_minutes': duration
                                        }
                                        availability_info['time_slots_with_duration'].append(time_slot)
                                        print(f"⏱️  Duration for {text}: {duration} minutes")
                    except Exception as e:
                        continue
                
            except Exception as e:
                print(f"⚠️  Error extracting specific elements: {e}")
            
            # Clean up the availability text
            if availability_info['availability_text']:
                availability_info['availability_text'] = availability_info['availability_text'].rstrip(' | ')
            
            return availability_info
            
        except Exception as e:
            print(f"❌ Error extracting availability info: {e}")
            return None
    
    def check_alice_marble(self, date_input=None):
        """Check Alice Marble tennis court availability"""
        url = "https://rec.us/alicemarble"
        return self.check_tennis_availability(url, "Alice Marble", date_input)
    
    def check_court_by_date(self, court_name, date_input):
        """Check any tennis court availability for a specific date"""
        # For now, we'll use Alice Marble as the example
        # In the future, this could be expanded to check different courts
        url = "https://rec.us/alicemarble"
        return self.check_tennis_availability(url, court_name, date_input)
    
    def load_court_urls(self):
        """Load tennis court URLs from the scraper results"""
        try:
            # Look for the most recent tennis_urls JSON file
            json_files = [f for f in os.listdir('.') if f.startswith('tennis_urls_') and f.endswith('.json')]
            if not json_files:
                print("❌ No tennis_urls JSON file found. Run the scraper first.")
                return []
            
            # Get the most recent file
            latest_file = max(json_files, key=os.path.getctime)
            print(f"📄 Loading court URLs from: {latest_file}")
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract tennis court URLs
            tennis_urls = data.get('tennis_urls', [])
            court_data = []
            
            for url_data in tennis_urls:
                url = url_data.get('url', '')
                text = url_data.get('text', '')
                
                # Filter for rec.us URLs (the actual booking pages)
                if 'rec.us' in url and any(keyword in text.lower() for keyword in ['tennis', 'court']):
                    court_name = text.strip() or url.split('/')[-1]
                    court_data.append({
                        'name': court_name,
                        'url': url,
                        'text': text
                    })
            
            print(f"🎾 Found {len(court_data)} tennis courts to check")
            return court_data
            
        except Exception as e:
            print(f"❌ Error loading court URLs: {e}")
            return []
    
    def check_single_court(self, court_data, date_input):
        """Check availability for a single court (used in parallel processing)"""
        court_name = court_data['name']
        url = court_data['url']
        
        # Create a new checker instance for this thread
        checker = TennisAvailabilityChecker(use_existing_session=False)
        
        try:
            if not checker.setup_driver():
                return {
                    'court': court_name,
                    'url': url,
                    'error': 'Failed to initialize driver',
                    'success': False
                }
            
            # Check availability
            availability = checker.check_tennis_availability(url, court_name, date_input)
            
            if availability:
                return {
                    'court': court_name,
                    'url': url,
                    'availability': availability,
                    'success': True
                }
            else:
                return {
                    'court': court_name,
                    'url': url,
                    'error': 'No availability data found',
                    'success': False
                }
                
        except Exception as e:
            return {
                'court': court_name,
                'url': url,
                'error': str(e),
                'success': False
            }
        finally:
            checker.close()
    
    def check_all_courts_parallel(self, date_input=None, max_workers=3):
        """Check all tennis courts in parallel"""
        # Load court URLs
        courts = self.load_court_urls()
        if not courts:
            return []
        
        print(f"\n🚀 Starting parallel check of {len(courts)} tennis courts...")
        print(f"📅 Date: {date_input or 'Next available'}")
        print(f"⚡ Max parallel workers: {max_workers}")
        
        results = []
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all court checks
            future_to_court = {
                executor.submit(self.check_single_court, court, date_input): court 
                for court in courts
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_court):
                court = future_to_court[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        times = result['availability'].get('available_times', [])
                        durations = result['availability'].get('time_slots_with_duration', [])
                        print(f"✅ {result['court']}: {len(times)} time slots found")
                    else:
                        print(f"❌ {result['court']}: {result['error']}")
                        
                except Exception as e:
                    print(f"❌ {court['name']}: Exception - {e}")
                    results.append({
                        'court': court['name'],
                        'url': court['url'],
                        'error': str(e),
                        'success': False
                    })
        
        return results
    
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
                
                # Try to restore focus to the previous application (only if not headless)
                try:
                    import subprocess
                    # Use AppleScript to focus on the previous application
                    subprocess.run([
                        'osascript', '-e', 
                        'tell application "System Events" to set frontmost of first process whose frontmost is true to true'
                    ], check=False, capture_output=True)
                    print("🔄 Attempted to restore focus to previous application")
                except Exception as e:
                    print(f"⚠️  Could not restore focus: {e}")
                    
            except Exception as e:
                # Check if it's the expected "no connection" error in headless mode
                if "Tried to run command without establishing a connection" in str(e):
                    print("🔒 Browser closed (headless mode cleanup)")
                else:
                    print(f"⚠️  Error closing browser: {e}")
                # Force quit if there's an issue
                try:
                    self.driver.quit()
                except:
                    pass

def main():
    """Main function to run the availability checker"""
    import sys
    
    print("🎾 Tennis Court Availability Checker")
    print("=" * 50)
    
    # Check for command line arguments
    date_input = None
    check_all = False
    max_workers = 3
    
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        
        # Check for special flags
        if '--all' in args or '-a' in args:
            check_all = True
            args.remove('--all' if '--all' in args else '-a')
        
        if '--workers' in args:
            try:
                worker_idx = args.index('--workers')
                max_workers = int(args[worker_idx + 1])
                args.pop(worker_idx)
                args.pop(worker_idx)
            except (ValueError, IndexError):
                print("⚠️  Invalid --workers value, using default (3)")
        
        # Remaining args are the date input
        if args:
            date_input = ' '.join(args)
            print(f"📅 Date input: {date_input}")
    
    if check_all:
        print("🚀 Checking ALL tennis courts in parallel...")
        checker = TennisAvailabilityChecker(use_existing_session=False)
        
        try:
            # Check all courts in parallel
            results = checker.check_all_courts_parallel(date_input, max_workers)
            
            # Display summary results
            print(f"\n📊 SUMMARY RESULTS:")
            print("=" * 60)
            
            successful_checks = [r for r in results if r['success']]
            failed_checks = [r for r in results if not r['success']]
            
            print(f"✅ Successful: {len(successful_checks)} courts")
            print(f"❌ Failed: {len(failed_checks)} courts")
            
            if successful_checks:
                print(f"\n🎾 COURTS WITH AVAILABILITY:")
                for result in successful_checks:
                    court = result['court']
                    availability = result['availability']
                    times = availability.get('available_times', [])
                    durations = availability.get('time_slots_with_duration', [])
                    
                    print(f"\n  {court}:")
                    if times:
                        print(f"    Times: {', '.join(times)}")
                    if durations:
                        print(f"    Slots with Duration:")
                        for slot in durations:
                            print(f"      {slot['time']}: {slot['duration_minutes']} minutes")
                    else:
                        print(f"    No specific time slots found")
            
            if failed_checks:
                print(f"\n❌ FAILED CHECKS:")
                for result in failed_checks:
                    print(f"  {result['court']}: {result['error']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in parallel checking: {e}")
            return False
        finally:
            checker.close()
    
    else:
        # Single court check (Alice Marble)
        print("🎾 Checking Alice Marble tennis court...")
        checker = TennisAvailabilityChecker(use_existing_session=True)
        
        try:
            # Set up the driver
            if not checker.setup_driver():
                return False
            
            # Check Alice Marble availability
            availability = checker.check_alice_marble(date_input)
            
            if availability:
                print(f"\n📊 Availability Results:")
                print(f"  Court: Alice Marble")
                print(f"  Has Availability: {'✅ Yes' if availability['has_availability'] else '❌ No'}")
                print(f"  Availability Text: {availability['availability_text']}")
                print(f"  Next Available: {availability['next_available']}")
                print(f"  Operating Hours: {availability['operating_hours']}")
                
                if availability['available_times']:
                    print(f"  Available Times: {', '.join(set(availability['available_times']))}")
                else:
                    print(f"  Available Times: No specific times found")
                
                if availability['time_slots_with_duration']:
                    print(f"  Time Slots with Duration:")
                    for slot in availability['time_slots_with_duration']:
                        print(f"    {slot['time']}: {slot['duration_minutes']} minutes")
                else:
                    print(f"  Time Slots with Duration: No duration info found")
                
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

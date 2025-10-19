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
            
            # Try to click on the next available date to get specific times
            self.click_next_available_date()
            
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
    
    def click_next_available_date(self):
        """Try to click on the next available date to get specific times"""
        try:
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

#!/usr/bin/env python3
"""
Google Maps URL Extractor
Connects to existing Chrome instance and extracts URLs from specific div/anchor patterns.
"""

import os
import sys
import time
import traceback
import csv
import re
import random
from datetime import datetime
from typing import List, Dict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class MapsURLExtractor:
    DEBUG_URL_DEFAULT = "http://127.0.0.1:9222/json/version"
    DEBUGGER_ADDRESS_DEFAULT = "127.0.0.1:9222"
    
    def __init__(
        self,
        debugger_address: str = None,
        debug_url: str = None,
        chromedriver_path_env: str = "CHROMEDRIVER_PATH",
        connect_timeout: int = 5,
        csv_filename: str = "google_scrape.csv"
    ):
        """
        Initializes the Selenium Chrome driver by attaching to an already running
        Chrome instance launched with --remote-debugging-port=9222.
        
        Args:
            csv_filename: Name of the CSV file to store extracted data
        """
        self.debugger_address = debugger_address or self.DEBUGGER_ADDRESS_DEFAULT
        self.debug_url = debug_url or self.DEBUG_URL_DEFAULT
        self.chromedriver_path_env = chromedriver_path_env
        self.connect_timeout = connect_timeout
        self.csv_filename = csv_filename
        self._initialize_csv_file()
        self.driver = self._selenium_get_driver()

    def _initialize_csv_file(self):
        """
        Initialize the CSV file with headers if it doesn't exist.
        """
        csv_headers = [
            'Name',
            'Rating',
            'Address',
            'GoogleMapsUri',
            'WebsiteUri',
            'PlaceId',
            'Types'
        ]
        
        # Check if file exists and has content
        file_exists = os.path.exists(self.csv_filename)
        file_has_content = file_exists and os.path.getsize(self.csv_filename) > 0
        
        if not file_has_content:
            print(f"📝 Creating CSV file: {self.csv_filename}")
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
                writer.writeheader()
        else:
            print(f"📝 Using existing CSV file: {self.csv_filename}")

    def _jittered_sleep(self, base_time: float, jitter: float = 0.2):
        """
        Sleep for a randomized amount of time to simulate human behavior.
        
        Args:
            base_time: Base sleep time in seconds
            jitter: Random variation range (±jitter seconds)
        """
        actual_time = base_time + random.uniform(-jitter, jitter)
        # Ensure we don't sleep for negative time
        actual_time = max(0.1, actual_time)
        time.sleep(actual_time)

    def _clean_text(self, text: str) -> str:
        """
        Clean text from encoding issues and unwanted characters.
        
        Args:
            text: Raw text that may have encoding issues
            
        Returns:
            Cleaned text with proper UTF-8 encoding
        """
        if not text:
            return ""
        
        try:
            cleaned_text = text
            
            # Try to fix double encoding by attempting different decode/encode cycles
            try:
                # Check if this looks like UTF-8 encoded as latin-1 (common issue)
                if 'Ã' in cleaned_text or 'â€' in cleaned_text or 'î' in cleaned_text:
                    # Try to decode as latin-1 and encode as utf-8
                    temp = cleaned_text.encode('latin-1').decode('utf-8')
                    cleaned_text = temp
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass  # Keep the current text if conversion fails
            
            # Common problematic patterns and their fixes
            replacements = [
                ('Ã¡', 'á'), ('Ã©', 'é'), ('Ã­', 'í'), ('Ã³', 'ó'), ('Ãº', 'ú'),
                ('Ã±', 'ñ'), ('Ã§', 'ç'), ('Ã ', 'à'), ('Ã¨', 'è'), ('Ã¬', 'ì'),
                ('Ã²', 'ò'), ('Ã¹', 'ù'), ('Ã¤', 'ä'), ('Ã«', 'ë'), ('Ã¯', 'ï'),
                ('Ã¶', 'ö'), ('Ã¼', 'ü'), ('îƒˆ', ''), ('â€™', "'"), ('â€œ', '"'),
                ('â€', '"'), ('â€¢', '•'), ('â‚¬', '€'), ('Â°', '°'), ('Â®', '®'),
                ('Â©', '©'), ('Â»', '»'), ('Â«', '«'), ('â€"', '–'), ('â€"', '—'),
                # Remove non-breaking spaces and other invisible characters
                ('\xa0', ' '), ('\u200b', ''), ('\u200c', ''), ('\u200d', ''), ('\ufeff', ''),
                # Clean up common weird sequences
                ('  ', ' '), ('\n', ' '), ('\r', ' '), ('\t', ' ')
            ]
            
            # Apply all replacements
            for old, new in replacements:
                cleaned_text = cleaned_text.replace(old, new)
            
            # Final cleanup - normalize whitespace
            cleaned_text = ' '.join(cleaned_text.split())
            
            return cleaned_text.strip()
            
        except Exception as e:
            print(f"⚠️  Error cleaning text '{text[:50]}...': {e}")
            # Return original text if cleaning fails
            return text.strip() if text else ""

    def _find_gcid_context(self, page_source: str, gcid_value: str) -> str:
        """
        Find the context around a GCID in the page source for debugging.
        
        Args:
            page_source: The full HTML page source
            gcid_value: The GCID value to search for (without 'gcid:' prefix)
            
        Returns:
            A snippet of text around the GCID, or empty string if not found
        """
        try:
            # Look for the gcid in the page source
            search_patterns = [f'gcid:{gcid_value}', f'gcid_{gcid_value}', f'"{gcid_value}"']
            
            for pattern in search_patterns:
                index = page_source.find(pattern)
                if index != -1:
                    # Get context around the gcid (50 characters before and after)
                    start = max(0, index - 50)
                    end = min(len(page_source), index + len(pattern) + 50)
                    context = page_source[start:end].replace('\n', ' ').replace('\r', ' ')
                    return context.strip()
            
            return ""
        except Exception:
            return ""

    def _extract_place_id(self, url: str) -> str:
        """
        Extract Place ID from Google Maps URL.
        
        Args:
            url: Google Maps URL
            
        Returns:
            Place ID if found, empty string otherwise
        """
        try:
            # Common patterns for Place ID in Google Maps URLs
            place_id_patterns = [
                r'place/[^/]+/data=.*?([a-zA-Z0-9_-]{20,})',  # data parameter
                r'place_id=([a-zA-Z0-9_-]{20,})',  # direct place_id parameter
                r'/place/([^/]+)',  # place name (not actual ID but identifier)
                r'data=.*?0x[a-fA-F0-9]+:0x([a-fA-F0-9]+)',  # hex coordinates format
                r'@(-?\d+\.\d+),(-?\d+\.\d+)',  # coordinates
            ]
            
            for pattern in place_id_patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
                    
        except Exception as e:
            print(f"⚠️  Error extracting Place ID: {e}")
            
        return ""

    def _append_to_csv(self, url_info: Dict[str, str]):
        """
        Append a single extracted record to the CSV file.
        
        Args:
            url_info: Dictionary containing extracted URL and content information
        """
        try:
            # Extract Place ID from Google Maps URL
            place_id = self._extract_place_id(url_info.get('url', ''))
            
            # Prepare the row data with new column structure
            name = url_info.get('content', {}).get('name', '') or url_info.get('text', '')
            row_data = {
                'Name': self._clean_text(name) if name else '',
                'Rating': url_info.get('content', {}).get('rating', ''),
                'Address': url_info.get('content', {}).get('address', ''),
                'GoogleMapsUri': url_info.get('url', ''),
                'WebsiteUri': url_info.get('content', {}).get('website', ''),
                'PlaceId': place_id,
                'Types': url_info.get('content', {}).get('category', '')
            }
            
            # Append to CSV file
            with open(self.csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Name', 'Rating', 'Address', 'GoogleMapsUri', 'WebsiteUri', 'PlaceId', 'Types']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(row_data)
            
            business_name = row_data['Name'] or 'Unknown Business'
            print(f"💾 [{url_info.get('index')}] Saved to CSV: {business_name}")
            
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")

    def _fetch_debugger_version(self) -> dict:
        """Fetch Chrome debugger version info."""
        req = Request(self.debug_url, headers={"User-Agent": "python-urllib/3"})
        with urlopen(req, timeout=self.connect_timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)

    def _get_local_chromedriver_service(self) -> Service:
        """Get ChromeDriver service from environment variable."""
        path = os.environ.get(self.chromedriver_path_env)
        if not path:
            raise EnvironmentError(
                f"{self.chromedriver_path_env} is not set. "
                "Set it to your local chromedriver executable path.\n"
                "Example (PowerShell): "
                f"$env:{self.chromedriver_path_env} = 'C:\\WebDrivers\\chromedriver.exe'"
            )
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{self.chromedriver_path_env} points to a non-existing file: {path}"
            )
        return Service(path)

    def _attach_to_debugger(self) -> webdriver.Chrome:
        """Attach to existing Chrome instance via debugger."""
        opts = Options()
        opts.add_experimental_option("debuggerAddress", self.debugger_address)
        service = self._get_local_chromedriver_service()
        return webdriver.Chrome(service=service, options=opts)

    def _selenium_get_driver(self) -> webdriver.Chrome:
        """Initialize and return Chrome driver attached to existing instance."""
        # Ensure local addresses bypass proxies
        os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
        os.environ.setdefault("no_proxy", "127.0.0.1,localhost")
        
        try:
            info = self._fetch_debugger_version()
        except (HTTPError, URLError) as e:
            print("ERROR: Cannot reach Chrome at", self.debug_url)
            print("Make sure you started Chrome like:")
            print(
                r'  & "C:\Program Files\Google\Chrome\Application\chrome.exe" '
                r'--remote-debugging-port=9222 '
                r'--user-data-dir="C:\tmp\selenium-profile"'
            )
            traceback.print_exception(e, e, e.__traceback__, file=sys.stdout)
            sys.exit(1)

        print("Chrome:", info.get("Browser"))
        driver = self._attach_to_debugger()
        print("Attached to Chrome")
        
        try:
            print("Current URL:", driver.current_url)
        except Exception:
            pass
            
        return driver

    def extract_map_urls(self, wait_time: int = 5, enable_interaction: bool = True) -> List[Dict[str, str]]:
        """
        Extract URLs from anchor tags that follow the specific div pattern.
        
        Args:
            wait_time: Time to wait for page loading
            enable_interaction: Whether to hover and click elements to fetch content
        
        Returns:
            List of dictionaries containing URL and any associated text
        """
        print("🔍 Looking for div elements with class 'Nv2PK THOPZb CpccDe'...")
        
        # Wait a moment for page to load
        self._jittered_sleep(wait_time)
        
        extracted_urls = []
        
        try:
            # Find all div elements with the specific class pattern
            target_divs = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "div.Nv2PK.THOPZb.CpccDe"
            )
            
            print(f"📋 Found {len(target_divs)} div elements matching the pattern")
            
            for i, div in enumerate(target_divs, 1):
                try:
                    print(f"\n🔍 Processing element [{i}/{len(target_divs)}]...")
                    
                    # Look for anchor tag with class "hfpxzc" after this div
                    anchor = self._find_associated_anchor(div, i)
                    
                    if anchor:
                        href = anchor.get_attribute("href")
                        anchor_text = anchor.text.strip()
                        
                        if href:
                            url_info = {
                                "index": i,
                                "url": href,
                                "text": anchor_text,
                                "div_id": div.get_attribute("id") or f"div_{i}",
                                "content": {}
                            }
                            
                            # Hover and click to fetch content if enabled
                            if enable_interaction:
                                content = self._interact_and_extract_content(anchor, div, i)
                                url_info["content"] = content
                            
                            extracted_urls.append(url_info)
                            
                            # Save to CSV immediately
                            self._append_to_csv(url_info)
                            
                            print(f"✅ [{i}] Found URL: {href}")
                            if anchor_text:
                                print(f"    Text: {anchor_text}")
                        else:
                            print(f"⚠️  [{i}] Anchor found but no href attribute")
                    else:
                        print(f"❌ [{i}] No anchor with class 'hfpxzc' found for this div")
                        
                except Exception as e:
                    print(f"❌ [{i}] Error processing div: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error finding target divs: {e}")
            return []
        
        return extracted_urls

    def _find_associated_anchor(self, div, index: int):
        """Find the anchor tag associated with a div element."""
        anchor = None
        
        # Method 1: Look for anchor as a child of this div
        try:
            anchor = div.find_element(By.CSS_SELECTOR, "a.hfpxzc")
        except NoSuchElementException:
            pass
        
        # Method 2: Look for anchor as a following sibling
        if not anchor:
            try:
                anchor = div.find_element(By.XPATH, "./following-sibling::*//a[@class='hfpxzc']")
            except NoSuchElementException:
                pass
        
        # Method 3: Look for anchor anywhere after this div in the DOM
        if not anchor:
            try:
                # Get parent and search from there
                parent = div.find_element(By.XPATH, "./..")
                anchor = parent.find_element(By.CSS_SELECTOR, "a.hfpxzc")
            except NoSuchElementException:
                pass
        
        return anchor

    def _interact_and_extract_content(self, anchor, div, index: int) -> Dict[str, str]:
        """
        Hover and click on anchor to trigger content loading, then extract information.
        
        Args:
            anchor: The anchor element to interact with
            div: The associated div element
            index: Element index for logging
            
        Returns:
            Dictionary containing extracted content
        """
        content = {}
        
        try:
            print(f"🖱️  [{index}] Hovering over anchor...")
            
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", anchor)
            self._jittered_sleep(0.8)  # Reduced from 1 second, with jitter
            
            # Create action chain for hovering
            actions = ActionChains(self.driver)
            actions.move_to_element(anchor).perform()
            self._jittered_sleep(1.5)  # Reduced from 2 seconds, with jitter
            
            print(f"👆 [{index}] Clicking anchor...")
            
            # Click the anchor
            try:
                anchor.click()
            except Exception as click_error:
                print(f"⚠️  [{index}] Direct click failed, trying JavaScript click: {click_error}")
                self.driver.execute_script("arguments[0].click();", anchor)
            
            # Wait for content to load
            self._jittered_sleep(2.5)  # Reduced from 3 seconds, with jitter
            
            print(f"📄 [{index}] Extracting content...")
            
            # Extract content from the loaded page/panel
            content = self._extract_loaded_content(index)
            
            # Optional: Go back or close panel to continue with next element
            # You might need to adjust this based on how Google Maps behaves
            try:
                # Try to find and click a close button or go back
                close_button = self.driver.find_element(By.CSS_SELECTOR, "[data-value='back'], .VfPpkd-icon-LgbsSe-OWXEXe-dgl2Hf")
                close_button.click()
                self._jittered_sleep(0.8)  # Reduced from 1 second, with jitter
            except NoSuchElementException:
                # If no close button, try pressing Escape
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                self._jittered_sleep(0.8)  # Reduced from 1 second, with jitter
            
        except Exception as e:
            print(f"❌ [{index}] Error during interaction: {e}")
        
        return content

    def _extract_loaded_content(self, index: int) -> Dict[str, str]:
        """
        Extract content from the loaded page after clicking an anchor.
        
        Args:
            index: Element index for logging
            
        Returns:
            Dictionary containing extracted content
        """
        content = {}
        
        try:
            # Wait a moment for content to load
            self._jittered_sleep(1.8)  # Reduced from 2 seconds, with jitter
            
            # Extract common elements that appear after clicking on a Maps result
            
            # Business name
            try:
                name_selectors = [
                    "h1[data-attrid='title']",
                    "h1.DUwDvf",
                    ".x3AX1-LfntMc-header-title-title",
                    "[data-attrid='title']"
                ]
                for selector in name_selectors:
                    try:
                        name_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        content["name"] = self._clean_text(name_element.text.strip())
                        break
                    except NoSuchElementException:
                        continue
            except Exception:
                pass
            
            # Address
            try:
                address_found = False
                address_selectors = [
                    "[data-item-id='address']",
                    ".Io6YTe",
                    ".rogA2c .Io6YTe",
                    "[aria-label*='address']",
                    "[aria-label*='dirección']",
                    "button[data-item-id*='address']",
                    "span[aria-label*='address']",
                    "span[aria-label*='dirección']"
                ]
                
                for selector in address_selectors:
                    try:
                        address_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        address_text = address_element.text.strip() or address_element.get_attribute("aria-label") or ""
                        if address_text:
                            content["address"] = self._clean_text(address_text)
                            address_found = True
                            break
                    except NoSuchElementException:
                        continue
                
                # If not found with selectors, try regex search in page source
                if not address_found:
                    try:
                        page_source = self.driver.page_source
                        
                        # Look for address patterns in the HTML
                        address_patterns = [
                            r'"location_on_googblue_24dp\.png","([^"]+)"',  # Location icon pattern
                            r'"([^"]*\d{5}[^"]*(?:Barcelona|Madrid|Valencia|Sevilla|Bilbao)[^"]*)"',  # Spanish addresses with postal codes
                            r'"([^"]*(?:Plaça|Plaza|Calle|Carrer|Avenida)[^"]+)"'  # Spanish street patterns
                        ]
                        
                        for pattern in address_patterns:
                            matches = re.findall(pattern, page_source, re.IGNORECASE)
                            for match in matches:
                                clean_address = match.strip()
                                # Validate it looks like an address (has some typical components)
                                if any(keyword in clean_address.lower() for keyword in ['plaça', 'plaza', 'calle', 'carrer', 'avenida', 'av.', 'c/', 'street', 'st.']):
                                    content["address"] = self._clean_text(clean_address)
                                    address_found = True
                                    print(f"📍 [{index}] Found address via regex: {clean_address}")
                                    break
                            if address_found:
                                break
                                
                    except Exception as regex_error:
                        print(f"⚠️  [{index}] Regex address search failed: {regex_error}")
                        
            except Exception as e:
                print(f"⚠️  [{index}] Address extraction error: {e}")
            
            # Phone number
            try:
                phone_found = False
                phone_selectors = [
                    "[data-item-id='phone']",
                    ".rogA2c [data-item-id*='phone']",
                    "button[data-item-id*='phone']",
                    "[aria-label*='phone']",
                    "[aria-label*='teléfono']",
                    ".Io6YTe[aria-label*='phone']",
                    ".Io6YTe[aria-label*='teléfono']",
                    "span[aria-label*='phone']",
                    "span[aria-label*='teléfono']"
                ]
                
                for selector in phone_selectors:
                    try:
                        phone_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        phone_text = phone_element.text.strip() or phone_element.get_attribute("aria-label") or ""
                        if phone_text and any(char.isdigit() for char in phone_text):
                            content["phone"] = self._clean_text(phone_text)
                            phone_found = True
                            break
                    except NoSuchElementException:
                        continue
                
                # If not found with selectors, try regex search in page source
                if not phone_found:
                    try:
                        page_source = self.driver.page_source
                        
                        # Look for phone patterns in the HTML - specifically after call_googblue icon
                        phone_patterns = [
                            r'call_googblue[^"]*\.png","([^"]+)"',  # Most specific: after call_googblue PNG
                            r'"call_googblue_24dp\.png","([0-9\s\+\-\(\)]{6,})"',  # Your specific pattern with digits
                            r'call_googblue.*?"([0-9]{3}\s[0-9]{2}\s[0-9]{2}\s[0-9]{2})"',  # Spanish format after call icon
                            r'call_googblue.*?"(\+?[0-9\s\-\(\)]{6,})"',  # General phone after call icon
                            r'system_gm/2x/call_googblue[^"]*\.png[^"]*","([^"]+)"'  # Full call icon path pattern
                        ]
                        
                        for i, pattern in enumerate(phone_patterns, 1):
                            matches = re.findall(pattern, page_source)
                            print(f"🔍 [{index}] Phone pattern {i}: found {len(matches)} matches")
                            for match in matches:
                                # Clean and validate the match
                                clean_phone = match.strip()
                                print(f"   └─ Raw match: '{clean_phone}'")
                                # Check if it looks like a phone number (has digits and reasonable length)
                                if re.search(r'\d{6,}', clean_phone.replace(' ', '').replace('-', '')):
                                    content["phone"] = self._clean_text(clean_phone)
                                    phone_found = True
                                    print(f"📞 [{index}] Found phone via regex pattern {i}: {clean_phone}")
                                    break
                            if phone_found:
                                break
                                
                    except Exception as regex_error:
                        print(f"⚠️  [{index}] Regex phone search failed: {regex_error}")
                        
            except Exception as e:
                print(f"⚠️  [{index}] Phone extraction error: {e}")
            
            # Rating
            try:
                rating_selectors = [
                    ".MW4etd",
                    ".ceNzKf"
                ]
                for selector in rating_selectors:
                    try:
                        rating_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        content["rating"] = self._clean_text(rating_element.text.strip())
                        break
                    except NoSuchElementException:
                        continue
            except Exception:
                pass
            
            # Website
            try:
                website_selectors = [
                    "[data-item-id='authority']",
                    "a[data-item-id='authority']"
                ]
                for selector in website_selectors:
                    try:
                        website_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        website_text = website_element.get_attribute("href") or website_element.text.strip()
                        content["website"] = self._clean_text(website_text) if website_text else ""
                        break
                    except NoSuchElementException:
                        continue
            except Exception:
                pass
            
            # Hours
            try:
                hours_found = False
                hours_selectors = [
                    "[data-item-id='oh']",
                    ".t39EBf",
                    "[aria-label*='hours']",
                    "[aria-label*='horario']",
                    "button[data-item-id*='oh']",
                    "span[aria-label*='hours']",
                    "span[aria-label*='horario']"
                ]
                
                for selector in hours_selectors:
                    try:
                        hours_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        hours_text = hours_element.text.strip() or hours_element.get_attribute("aria-label") or ""
                        if hours_text:
                            content["hours"] = self._clean_text(hours_text)
                            hours_found = True
                            break
                    except NoSuchElementException:
                        continue
                
                # If not found with selectors, try regex search in page source
                if not hours_found:
                    try:
                        page_source = self.driver.page_source
                        
                        # Look for hours patterns in the HTML
                        hours_patterns = [
                            r'"schedule_googblue_24dp\.png","([^"]+)"',  # Schedule icon pattern
                            r'"(Abierto[^"]*)"',  # Spanish "Open" pattern
                            r'"(Cerrado[^"]*)"',  # Spanish "Closed" pattern
                            r'"(Open[^"]*)"',  # English "Open" pattern
                            r'"(Closed[^"]*)"',  # English "Closed" pattern
                            r'"([^"]*\d{1,2}:\d{2}[^"]*)"'  # Time patterns
                        ]
                        
                        for pattern in hours_patterns:
                            matches = re.findall(pattern, page_source, re.IGNORECASE)
                            for match in matches:
                                clean_hours = match.strip()
                                # Validate it looks like hours information
                                if any(keyword in clean_hours.lower() for keyword in ['abierto', 'cerrado', 'open', 'closed', ':', 'am', 'pm', 'horario', 'hours']):
                                    content["hours"] = self._clean_text(clean_hours)
                                    hours_found = True
                                    print(f"🕐 [{index}] Found hours via regex: {clean_hours}")
                                    break
                            if hours_found:
                                break
                                
                    except Exception as regex_error:
                        print(f"⚠️  [{index}] Regex hours search failed: {regex_error}")
                        
            except Exception as e:
                print(f"⚠️  [{index}] Hours extraction error: {e}")
            
            # Category/Types
            try:
                types_found = False
                category_selectors = [
                    ".DkEaL",
                    ".YXMRrb",
                    "[data-attrid='kc:/collection/knowledge_panels/has_action:add_review']",
                    ".rogA2c .DkEaL",
                    "button[jsaction*='category']",
                    ".x3AX1-LfntMc-header-title .DkEaL"
                ]
                
                # Try to get multiple types/categories
                all_types = []
                
                for selector in category_selectors:
                    try:
                        category_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in category_elements:
                            category_text = element.text.strip()
                            if category_text and category_text not in all_types:
                                all_types.append(self._clean_text(category_text))
                    except NoSuchElementException:
                        continue
                
                if all_types:
                    content["category"] = " | ".join(all_types)  # Multiple types separated by |
                    types_found = True
                
                # If not found with selectors, try regex search in page source
                if not types_found:
                    try:
                        page_source = self.driver.page_source
                        
                        # Look for category/type patterns in the HTML
                        # First, specifically search for gcid patterns with more precision
                        gcid_patterns = [
                            r'"gcid:([a-zA-Z_]+)"',  # Most specific: quoted gcid
                            r'\bgcid:([a-zA-Z_]+)\b',  # Word boundary gcid
                            r'data-gcid="([^"]*)"',  # Data attribute gcid
                            r'gcid:([a-zA-Z_]+)',  # Basic gcid pattern
                            r'"gcid_([a-zA-Z_]+)"',  # Alternative gcid format
                            r'category_id["\']:[\s]*["\']gcid:([a-zA-Z_]+)["\']',  # JSON category_id with gcid
                        ]
                        
                        # Secondary patterns for fallback
                        fallback_patterns = [
                            r'"([^"]*(?:Restaurant|Bar|Cafe|Hotel|Shop|Store|Service|Centro|Tienda|Restaurante|Bar|Cafetería)[^"]*)"',
                            r'\"category\":\s*\"([^\"]+)\"',
                            r'\"types\":\s*\[([^\]]+)\]'
                        ]
                        
                        found_types = set()
                        gcid_found = False
                        
                        # First, try to find gcid patterns
                        print(f"🔍 [{index}] Searching for GCID patterns...")
                        for i, pattern in enumerate(gcid_patterns):
                            matches = re.findall(pattern, page_source, re.IGNORECASE)
                            print(f"   Pattern {i+1} ({pattern[:30]}...): {len(matches)} matches")
                            for match in matches:
                                clean_gcid = match.strip().strip('"')
                                if clean_gcid and len(clean_gcid) > 2:
                                    print(f"   ✅ Found GCID: '{clean_gcid}'")
                                    # Convert gcid format to readable format
                                    formatted_type = clean_gcid.replace('_', ' ').title()
                                    found_types.add(f"gcid:{clean_gcid}")  # Keep original gcid
                                    found_types.add(formatted_type)  # Add readable version
                                    gcid_found = True
                        
                        # Only use fallback patterns if no gcid was found
                        if not gcid_found:
                            print(f"🔍 [{index}] No GCID found, trying fallback patterns...")
                            for i, pattern in enumerate(fallback_patterns):
                                matches = re.findall(pattern, page_source, re.IGNORECASE)
                                print(f"   Fallback pattern {i+1}: {len(matches)} matches")
                                for match in matches:
                                    clean_type = match.strip().strip('"')
                                    if len(clean_type) > 2 and len(clean_type) < 50:
                                        # Filter out common non-category text
                                        if not any(exclude in clean_type.lower() for exclude in ['añadir', 'etiqueta', 'add', 'tag', 'label']):
                                            found_types.add(clean_type)
                                            print(f"   ✅ Added fallback type: '{clean_type}'")
                        
                        # Additional comprehensive search for gcid in various formats
                        if not gcid_found:
                            print(f"🔍 [{index}] Trying comprehensive gcid search...")
                            # Search for gcid in different contexts and formats
                            comprehensive_patterns = [
                                r'category[^:]*:\s*["\']?gcid:([a-zA-Z_]+)',
                                r'type[^:]*:\s*["\']?gcid:([a-zA-Z_]+)',
                                r'business_type[^:]*:\s*["\']?gcid:([a-zA-Z_]+)',
                                r'place_type[^:]*:\s*["\']?gcid:([a-zA-Z_]+)',
                                r'\["gcid:([a-zA-Z_]+)"\]',
                                r'gcid=([a-zA-Z_]+)',
                                r'cid["\s]*:["\s]*gcid:([a-zA-Z_]+)',
                            ]
                            
                            for pattern in comprehensive_patterns:
                                matches = re.findall(pattern, page_source, re.IGNORECASE)
                                for match in matches:
                                    clean_gcid = match.strip()
                                    if clean_gcid and len(clean_gcid) > 2:
                                        print(f"   ✅ Found comprehensive GCID: '{clean_gcid}'")
                                        formatted_type = clean_gcid.replace('_', ' ').title()
                                        found_types.add(f"gcid:{clean_gcid}")
                                        found_types.add(formatted_type)
                                        gcid_found = True
                        
                        if found_types:
                            # Prioritize gcid types first, then others
                            gcid_types = [t for t in found_types if t.startswith('gcid:')]
                            other_types = [t for t in found_types if not t.startswith('gcid:')]
                            
                            # Combine with gcid types first
                            all_found_types = gcid_types + other_types
                            content["category"] = " | ".join(all_found_types[:5])  # Limit to 5 types
                            
                            if gcid_types:
                                print(f"🏷️  [{index}] Found gcid types: {', '.join(gcid_types)}")
                                # Also save a sample of the page source around gcid for debugging
                                for gcid_type in gcid_types:
                                    gcid_value = gcid_type.replace('gcid:', '')
                                    gcid_context = self._find_gcid_context(page_source, gcid_value)
                                    if gcid_context:
                                        print(f"   📄 Context: ...{gcid_context}...")
                            
                            print(f"🏷️  [{index}] All found types: {content['category']}")
                        else:
                            print(f"⚠️  [{index}] No business types found via regex")
                                
                    except Exception as regex_error:
                        print(f"⚠️  [{index}] Regex types search failed: {regex_error}")
                        
            except Exception as e:
                print(f"⚠️  [{index}] Types extraction error: {e}")
            
            if content:
                print(f"📝 [{index}] Extracted content: {list(content.keys())}")
            else:
                print(f"⚠️  [{index}] No content extracted")
                
        except Exception as e:
            print(f"❌ [{index}] Error extracting content: {e}")
        
        return content

    def print_results(self, urls: List[Dict[str, str]]) -> None:
        """Print extracted URLs in a formatted way."""
        print("\n" + "="*80)
        print(f"📊 EXTRACTION RESULTS - Found {len(urls)} URLs")
        print("="*80)
        
        if not urls:
            print("❌ No URLs were extracted")
            return
        
        for url_info in urls:
            print(f"\n[{url_info['index']}] DIV ID: {url_info['div_id']}")
            print(f"    URL: {url_info['url']}")
            if url_info['text']:
                print(f"    Text: {url_info['text']}")
            print("-" * 60)

    def save_results_to_file(self, urls: List[Dict[str, str]], filename: str = "extracted_urls.json") -> None:
        """Save extracted URLs to a JSON file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(urls, f, ensure_ascii=False, indent=2)
            print(f"💾 Results saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving to file: {e}")

    def close(self):
        """Close the driver connection."""
        if hasattr(self, 'driver') and self.driver:
            print("🔌 Closing driver connection...")
            self.driver.quit()


def main():
    """Main function to run the URL extraction."""
    print("🚀 Starting Google Maps URL Extractor")
    print("Make sure Chrome is running with:")
    print('& "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\tmp\\selenium-profile"')
    print()
    
    # Ask for CSV filename
    csv_filename = input("📄 Enter CSV filename (default: google_scrape.csv): ").strip()
    if not csv_filename:
        csv_filename = "google_scrape.csv"
    
    extractor = None
    
    try:
        # Initialize the extractor with custom CSV filename
        extractor = MapsURLExtractor(csv_filename=csv_filename)
        
        print(f"\n📊 Results will be saved to: {csv_filename}")
        print("💡 Data is saved continuously as each business is processed!")
        
        # Wait for user to navigate to the desired page
        input("\n📍 Navigate to the Google Maps page you want to scrape, then press Enter to continue...")
        
        # Ask user about interaction preferences
        print("\n⚙️  Extraction Options:")
        print("1. Basic extraction (fast, URLs only)")
        print("2. Interactive extraction (slower, includes business details)")
        
        choice = input("Choose extraction mode (1 or 2, default: 2): ").strip()
        enable_interaction = choice != "1"
        
        wait_time = 2  # Reduced default from 3 to 2 seconds
        if enable_interaction:
            wait_input = input("⏱️  Wait time between interactions in seconds (default: 2): ").strip()
            if wait_input.isdigit():
                wait_time = int(wait_input)
        
        # Extract URLs
        print(f"\n🔍 Starting {'interactive' if enable_interaction else 'basic'} URL extraction...")
        urls = extractor.extract_map_urls(wait_time=wait_time, enable_interaction=enable_interaction)
        
        # Print results
        extractor.print_results(urls)
        
        print(f"\n📊 All extracted data has been saved to: {csv_filename}")
        print(f"📈 Total records processed: {len(urls)}")
        
        # Optionally save to JSON file as well
        if urls:
            save_choice = input("\n💾 Also save results to JSON file? (y/n): ").lower().strip()
            if save_choice == 'y':
                filename = input("📝 Enter JSON filename (default: extracted_urls.json): ").strip()
                if not filename:
                    filename = "extracted_urls.json"
                extractor.save_results_to_file(urls, filename)
        
        print("\n✅ Extraction completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Extraction interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        traceback.print_exc()
    finally:
        if extractor:
            extractor.close()


if __name__ == "__main__":
    main()

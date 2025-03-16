import time
import json
import os
import re
import random
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from src.scrapers.scraper_base import ScraperBase
from src.utils.browser import wait_for_element, random_sleep, element_exists, setup_browser, scroll_to_bottom
from src.utils.logger import get_default_logger
from src.utils.error_handler import retry_on_exception, handle_selenium_exceptions, log_execution_time
from src.utils.human_behavior import HumanBehaviorSimulator

# Get logger
logger = get_default_logger()

# Instagram URLs
PROFILE_URL = "https://www.instagram.com/{}/"
FOLLOWERS_URL = "https://www.instagram.com/{}/followers/"

# Profile selectors (for fallback)
PROFILE_STATS = "section ul"
PROFILE_POSTS_COUNT = "li:nth-child(1) span"
PROFILE_FOLLOWERS_COUNT = "li:nth-child(2) span"
PROFILE_FOLLOWING_COUNT = "li:nth-child(3) span"
ACCOUNT_TYPE_BADGE = "div[style*='flex-direction'] > div > div > div > span"
PRIVATE_ACCOUNT_INDICATOR = "h2 ~ div span"

class FollowerScraper(ScraperBase):
    """
    Scraper for collecting follower data from Instagram.
    Extracts follower data directly from the page source.
    """
    
    def __init__(self, target_username=None):
        """
        Initialize the follower scraper.
        
        Args:
            target_username: The username whose followers to scrape. If None, uses the logged-in user.
        """
        super().__init__()
        self.target_username = target_username
        self.followers_data = []
        self.user_id = None
        self.data_dir = os.path.join("data", "followers")
        self.skip_profile_analysis = False  # Default to analyzing profiles
        os.makedirs(self.data_dir, exist_ok=True)
    
    def run(self):
        """
        Main method to run the follower scraper.
        
        Returns:
            List of follower data dictionaries
        """
        logger.info("Starting follower data collection")
        
        try:
            # Only start the browser if it doesn't already exist
            if not self.browser:
                session_loaded = self.start()
                logger.info(f"Started new browser session. Session loaded: {session_loaded}")
            else:
                logger.info("Using existing browser session")
                # Initialize human behavior simulator if using existing browser
                if not self.human_behavior:
                    self.human_behavior = HumanBehaviorSimulator(self.browser)
                    logger.info("Initialized human behavior simulator for existing browser")
            
            # Set target username to logged-in user if not specified
            if not self.target_username:
                self.target_username = self.username
            
            # Navigate to profile and extract user ID
            self._extract_user_id_from_profile()
            
            if not self.user_id:
                logger.error("Failed to get user ID. Cannot proceed with follower collection.")
                return []
            
            # Navigate to followers page and extract follower data
            self._extract_followers_from_page()
            
            # Analyze follower profiles (only if not skipped)
            if not self.skip_profile_analysis:
                logger.info("Analyzing follower profiles in detail")
                self.analyze_follower_profiles()
            else:
                logger.info("Skipping profile analysis as requested")
            
            # Save the data
            self.save_follower_data()
            
            logger.info(f"Follower data collection completed. Collected {len(self.followers_data)} followers.")
            return self.followers_data
            
        except Exception as e:
            logger.error(f"Follower scraping failed: {str(e)}")
            raise
        finally:
            # Only stop the browser if we started it
            if not hasattr(self, '_browser_passed_externally') or not self._browser_passed_externally:
                self.stop()
            else:
                logger.info("Not closing browser as it was passed externally")
    
    @retry_on_exception(max_retries=3)
    @handle_selenium_exceptions
    def _extract_user_id_from_profile(self):
        """
        Navigate to profile and extract user ID from page source.
        """
        profile_url = PROFILE_URL.format(self.target_username)
        logger.info(f"Navigating to profile: {profile_url}")
        
        self.navigate_to(profile_url)
        
        # Wait for the page to load
        self.human_behavior.random_sleep(3, 5)
        
        # Try to extract user ID from page source
        try:
            page_source = self.browser.page_source
            
            # Try different regex patterns to find user ID
            user_id_patterns = [
                r'"user_id":"(\d+)"',
                r'"profilePage_(\d+)"',
                r'"owner":{"id":"(\d+)"',
                r'"id":"(\d+)","username":"{}"'.format(self.target_username),
                r'instagram://user\?username={}&amp;userid=(\d+)'.format(self.target_username),
                r'"X-IG-App-ID":"(\d+)"',
                r'"user":{"id":"(\d+)"',
                r'"userId":"(\d+)"',
                r'"viewer_id":"(\d+)"',
                r'"viewerId":"(\d+)"',
                r'"ds_user_id=(\d+)"',
                r'"instapp:owner_user_id":"(\d+)"'
            ]
            
            for pattern in user_id_patterns:
                match = re.search(pattern, page_source)
                if match:
                    self.user_id = match.group(1)
                    logger.info(f"Found user ID: {self.user_id}")
                    break
            
            # If we still don't have the user ID, try JavaScript
            if not self.user_id:
                try:
                    # Try to extract from window._sharedData
                    self.user_id = self.browser.execute_script("""
                        if (window._sharedData && 
                            window._sharedData.entry_data && 
                            window._sharedData.entry_data.ProfilePage && 
                            window._sharedData.entry_data.ProfilePage[0] && 
                            window._sharedData.entry_data.ProfilePage[0].graphql && 
                            window._sharedData.entry_data.ProfilePage[0].graphql.user) {
                            return window._sharedData.entry_data.ProfilePage[0].graphql.user.id;
                        }
                        return null;
                    """)
                    
                    if self.user_id:
                        logger.info(f"Found user ID from _sharedData: {self.user_id}")
                except Exception as e:
                    logger.warning(f"Failed to extract user ID from _sharedData: {str(e)}")
            
            # If we still don't have the user ID, try another approach
            if not self.user_id:
                try:
                    # Try to extract from window.__additionalDataLoaded
                    self.user_id = self.browser.execute_script("""
                        for (const key in window) {
                            if (key.startsWith('__additionalData')) {
                                const data = window[key];
                                if (data && typeof data === 'object' && data.user && data.user.id) {
                                    return data.user.id;
                                }
                            }
                        }
                        return null;
                    """)
                    
                    if self.user_id:
                        logger.info(f"Found user ID from __additionalData: {self.user_id}")
                except Exception as e:
                    logger.warning(f"Failed to extract user ID from __additionalData: {str(e)}")
            
            # If we still don't have the user ID, try one more approach
            if not self.user_id:
                try:
                    # Try to extract from any script tag containing the user ID
                    scripts = self.browser.find_elements(By.TAG_NAME, "script")
                    for script in scripts:
                        try:
                            script_content = script.get_attribute("innerHTML")
                            if script_content and self.target_username in script_content:
                                for pattern in user_id_patterns:
                                    match = re.search(pattern, script_content)
                                    if match:
                                        self.user_id = match.group(1)
                                        logger.info(f"Found user ID from script tag: {self.user_id}")
                                        break
                                if self.user_id:
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Failed to extract user ID from script tags: {str(e)}")
            
            # Try to extract from meta tags
            if not self.user_id:
                try:
                    meta_tags = self.browser.find_elements(By.TAG_NAME, "meta")
                    for meta in meta_tags:
                        try:
                            content = meta.get_attribute("content")
                            if content and self.target_username in content:
                                for pattern in user_id_patterns:
                                    match = re.search(pattern, content)
                                    if match:
                                        self.user_id = match.group(1)
                                        logger.info(f"Found user ID from meta tag: {self.user_id}")
                                        break
                                if self.user_id:
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Failed to extract user ID from meta tags: {str(e)}")
            
            # Try to extract from cookies
            if not self.user_id:
                try:
                    cookies = self.browser.get_cookies()
                    for cookie in cookies:
                        if cookie['name'] == 'ds_user_id':
                            self.user_id = cookie['value']
                            logger.info(f"Found user ID from cookies: {self.user_id}")
                            break
                except Exception as e:
                    logger.warning(f"Failed to extract user ID from cookies: {str(e)}")
            
            # Try to extract from localStorage
            if not self.user_id:
                try:
                    local_storage = self.browser.execute_script("return Object.keys(localStorage);")
                    for key in local_storage:
                        try:
                            value = self.browser.execute_script(f"return localStorage.getItem('{key}');")
                            if value and self.target_username in value:
                                for pattern in user_id_patterns:
                                    match = re.search(pattern, value)
                                    if match:
                                        self.user_id = match.group(1)
                                        logger.info(f"Found user ID from localStorage: {self.user_id}")
                                        break
                                if self.user_id:
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Failed to extract user ID from localStorage: {str(e)}")
            
            # If we still don't have the user ID, we can't proceed
            if not self.user_id:
                logger.error("Could not find user ID. Cannot proceed with follower collection.")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract user ID: {str(e)}")
            return False
    
    @retry_on_exception(max_retries=3)
    @handle_selenium_exceptions
    @log_execution_time
    def _extract_followers_from_page(self):
        """
        Navigate to followers page and extract follower data.
        """
        try:
            # Navigate to followers page
            followers_url = f"https://www.instagram.com/{self.target_username}/followers/"
            logger.info(f"Navigating to followers page: {followers_url}")
            
            self.navigate_to(followers_url)
            
            # Wait for the page to load with a longer delay
            self.human_behavior.random_sleep(5, 8)
            
            # Check if we're being presented with a challenge or captcha
            if self._is_challenge_present():
                logger.error("Challenge or captcha detected. Cannot proceed with follower collection.")
                return
            
            # Try to click on the followers count to open the modal
            try:
                # First try to find the followers count element and click it
                logger.info("Trying to click on followers count to open modal")
                
                # Different selectors for the followers count element
                follower_count_selectors = [
                    f"a[href='/{self.target_username}/followers/']",
                    "a[href*='/followers/']",
                    "ul li a span",  # General structure for profile stats
                    "section main header section ul li:nth-child(2) a",  # Another common structure
                    "span[title*='follower']",
                    "span[title*='pengikut']",  # Indonesian language
                    "span[title*='Follower']"
                ]
                
                follower_count_element = None
                for selector in follower_count_selectors:
                    try:
                        elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            try:
                                text = element.text
                                # Check if this element contains a number (follower count)
                                if text and any(c.isdigit() for c in text):
                                    logger.info(f"Found potential follower count element with text: {text}")
                                    follower_count_element = element
                                    break
                            except:
                                continue
                        
                        if follower_count_element:
                            break
                    except:
                        continue
                
                # If we found the element, click it
                if follower_count_element:
                    logger.info("Clicking on follower count element")
                    follower_count_element.click()
                    self.human_behavior.random_sleep(3, 5)
                else:
                    logger.info("Could not find follower count element to click, proceeding with direct URL")
            except Exception as e:
                logger.warning(f"Error clicking on follower count: {str(e)}")
                logger.info("Proceeding with direct URL access")
            
            # Wait for the follower modal to appear
            logger.info("Waiting for follower list to load")
            self.human_behavior.random_sleep(3, 5)
            
            # First try the specialized method for Instagram follower modal
            try:
                # Check if a modal dialog is present
                dialogs = self.browser.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
                if dialogs and len(dialogs) > 0:
                    logger.info("Detected follower modal dialog, using specialized scrolling method")
                    followers_data = self._scroll_instagram_follower_modal()
                    if followers_data and len(followers_data) > 0:
                        logger.info(f"Successfully collected {len(followers_data)} followers using specialized method")
                        return
            except Exception as e:
                logger.warning(f"Specialized follower modal method failed: {str(e)}")
                logger.info("Falling back to standard method")
            
            # Continue with the standard method if specialized method failed
            # ... [rest of the existing method remains unchanged]
            
            # Try to find the follower list using various selectors
            follower_list_selectors = [
                "div[role='dialog'] ul",
                "div[role='dialog'] div[style*='overflow']",
                "div[role='dialog'] div[style*='auto']",
                "div[role='dialog'] div.ScrollableArea",
                "div._aano",  # Instagram's class for the follower list container
                "div.PZuss",  # Another Instagram class
                "div[aria-label*='Followers']",
                "div[aria-label*='follower']",
                "div[aria-label*='Pengikut']",  # Indonesian language
                # Add new selectors for the current Instagram UI
                "div[role='dialog'] div._ab8w._ab94._ab97._ab9f._ab9k._ab9p._abcm",
                "div[role='dialog'] div._aano",
                "div._aano",
                "div[role='dialog'] div[style*='position: relative']",
                "div[role='dialog'] div[style*='flex-direction: column']",
                "div[role='dialog'] div[style*='overflow-y']",
                "div[role='dialog'] div[style*='overflow: auto']",
                "div[role='dialog'] div[style*='overflow: scroll']",
                "div[role='dialog'] div[style*='overflow-y: auto']",
                "div[role='dialog'] div[style*='overflow-y: scroll']"
            ]
            
            # Log all dialog elements to help with debugging
            try:
                dialogs = self.browser.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
                logger.info(f"Found {len(dialogs)} dialog elements")
                
                if len(dialogs) > 0:
                    logger.info(f"First dialog classes: {dialogs[0].get_attribute('class')}")
            except Exception as e:
                logger.warning(f"Error inspecting dialogs: {str(e)}")
            
            # Find the follower list container
            follower_list = None
            for selector in follower_list_selectors:
                try:
                    logger.info(f"Trying to find follower list with selector: {selector}")
                    elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        # Try to find the one that contains user elements
                        for element in elements:
                            try:
                                # Check if this element contains links or usernames
                                links = element.find_elements(By.TAG_NAME, "a")
                                if links and len(links) > 0:
                                    follower_list = element
                                    logger.info(f"Found follower list with selector: {selector}")
                                    break
                            except:
                                continue
                        
                        if follower_list:
                            break
                except Exception as e:
                    logger.debug(f"Error finding element with selector {selector}: {str(e)}")
                    continue
            
            # If we still don't have a follower list, try a more dynamic approach
            if not follower_list:
                logger.info("Trying dynamic approach to find follower list")
                try:
                    # Look for any scrollable container that might be the follower list
                    scrollable_elements = self.browser.find_elements(By.XPATH, 
                        "//*[contains(@style, 'overflow') or contains(@style, 'scroll') or contains(@style, 'auto')]")
                    
                    logger.info(f"Found {len(scrollable_elements)} potentially scrollable elements")
                    
                    # Try to find the most likely follower list container
                    for element in scrollable_elements:
                        try:
                            # Check if this element contains user links
                            links = element.find_elements(By.TAG_NAME, "a")
                            profile_links = []
                            
                            for link in links:
                                href = link.get_attribute("href")
                                if href and "/p/" not in href and "/explore/" not in href and "instagram.com/" in href:
                                    profile_links.append(link)
                            
                            if profile_links:
                                logger.info(f"Found potential follower list with {len(profile_links)} profile links")
                                follower_list = element
                                break
                        except:
                            continue
                    
                    # If we still don't have a follower list, try to find the dialog and then find scrollable elements within it
                    if not follower_list:
                        dialogs = self.browser.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
                        if dialogs:
                            logger.info(f"Found {len(dialogs)} dialog elements, checking for scrollable elements within them")
                            for dialog in dialogs:
                                try:
                                    # Find all divs in the dialog
                                    divs = dialog.find_elements(By.TAG_NAME, "div")
                                    
                                    # Sort divs by size (larger divs are more likely to be the follower list container)
                                    sized_divs = []
                                    for div in divs:
                                        try:
                                            size = div.size
                                            if size['height'] > 100 and size['width'] > 100:  # Only consider reasonably sized divs
                                                sized_divs.append((div, size['height'] * size['width']))
                                        except:
                                            continue
                                    
                                    # Sort by size (largest first)
                                    sized_divs.sort(key=lambda x: x[1], reverse=True)
                                    
                                    # Check the largest divs first
                                    for div, _ in sized_divs[:10]:  # Check the 10 largest divs
                                        try:
                                            # Check if this div contains links to profiles
                                            links = div.find_elements(By.TAG_NAME, "a")
                                            profile_links = []
                                            
                                            for link in links:
                                                href = link.get_attribute("href")
                                                if href and "/p/" not in href and "/explore/" not in href and "instagram.com/" in href:
                                                    profile_links.append(link)
                                            
                                            if len(profile_links) > 3:  # If it has several profile links, it's likely the follower list
                                                logger.info(f"Found potential follower list with {len(profile_links)} profile links in dialog")
                                                follower_list = div
                                                break
                                        except:
                                            continue
                                    
                                    if follower_list:
                                        break
                                except:
                                    continue
                except Exception as e:
                    logger.warning(f"Error in dynamic follower list search: {str(e)}")
            
            # If we still can't find the follower list, try to extract follower data directly from the page
            if not follower_list:
                logger.info("Could not find follower list container, trying to extract followers directly")
                return self._extract_followers_directly()
            
            logger.info("Found follower list container, proceeding with extraction")
            
            # Get the total number of followers to track progress
            try:
                follower_count_text = None
                
                # Try to find the follower count in the dialog title
                title_elements = self.browser.find_elements(By.CSS_SELECTOR, "div[role='dialog'] h1")
                if title_elements:
                    for title in title_elements:
                        text = title.text
                        if text and ("follower" in text.lower() or "pengikut" in text.lower()):
                            # Extract the number from the title
                            count_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+k?)?)', text)
                            if count_match:
                                follower_count_text = count_match.group(1)
                                break
                
                # If we couldn't find it in the title, try the profile stats
                if not follower_count_text:
                    count_elements = self.browser.find_elements(By.CSS_SELECTOR, "span[title]")
                    for element in count_elements:
                        title = element.get_attribute("title")
                        if title and title.isdigit():
                            follower_count_text = title
                            break
                
                # Parse the follower count
                if follower_count_text:
                    # Remove commas and convert k/m to numbers
                    follower_count_text = follower_count_text.replace(',', '')
                    if 'k' in follower_count_text.lower():
                        follower_count = int(float(follower_count_text.lower().replace('k', '')) * 1000)
                    elif 'm' in follower_count_text.lower():
                        follower_count = int(float(follower_count_text.lower().replace('m', '')) * 1000000)
                    else:
                        follower_count = int(follower_count_text)
                    
                    logger.info(f"Total followers to collect: {follower_count}")
                else:
                    logger.warning("Could not determine total follower count")
                    follower_count = 0
            except Exception as e:
                logger.warning(f"Error determining follower count: {str(e)}")
                follower_count = 0
            
            # Set a reasonable limit for followers to collect - collect all followers if possible
            max_followers_to_collect = follower_count if follower_count > 0 else 100000
            logger.info(f"Will collect up to {max_followers_to_collect} followers")
            
            # Scroll to load followers
            previously_loaded_followers = 0
            no_new_followers_count = 0
            consecutive_same_count = 0
            max_scrolls = 10000  # Increased from 1000 to ensure we get all followers even for large accounts
            last_progress_log = 0
            
            # Initialize scroll tracking variables
            previous_height = self.browser.execute_script("return arguments[0].scrollHeight", follower_list)
            previous_position = self.browser.execute_script("return arguments[0].scrollTop", follower_list)
            no_progress_count = 0
            
            # Save the initial timestamp to implement a timeout
            start_time = time.time()
            max_time_seconds = 7200  # 2 hours maximum for very large follower lists
            
            # Try to get the total number of followers from the dialog title or other elements
            total_followers_count = 0
            try:
                # Look for elements that might contain the follower count
                count_elements = self.browser.find_elements(By.CSS_SELECTOR, 
                    "div[role='dialog'] h1, div[role='dialog'] div > span, span[title]")
                
                for element in count_elements:
                    try:
                        text = element.text
                        # Look for numbers in the text
                        if text and any(c.isdigit() for c in text):
                            # Extract numbers from the text
                            numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?(?:k|m|b)?', text)
                            if numbers:
                                # Parse the number (handle k, m, b suffixes)
                                number_text = numbers[0].lower()
                                if 'k' in number_text:
                                    total_followers_count = int(float(number_text.replace('k', '')) * 1000)
                                elif 'm' in number_text:
                                    total_followers_count = int(float(number_text.replace('m', '')) * 1000000)
                                elif 'b' in number_text:
                                    total_followers_count = int(float(number_text.replace('b', '')) * 1000000000)
                                else:
                                    total_followers_count = int(number_text.replace(',', ''))
                                
                                logger.info(f"Found potential follower count: {total_followers_count}")
                                break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error getting total followers count: {str(e)}")
            
            for scroll_count in range(max_scrolls):
                # Check if we've been scrolling for too long
                elapsed_time = time.time() - start_time
                if elapsed_time > max_time_seconds:
                    logger.warning(f"Scrolling timeout reached after {elapsed_time:.1f} seconds. Stopping scrolling.")
                    break
                
                if scroll_count % 10 == 0:
                    logger.info(f"Scroll {scroll_count + 1}/{max_scrolls} (Elapsed time: {elapsed_time:.1f}s)")
                
                # Extract current followers before scrolling
                follower_items = self._get_follower_items_from_container(follower_list)
                current_followers_count = len(follower_items)
                
                # Log progress periodically or when significant progress is made
                if current_followers_count - last_progress_log >= 100 or scroll_count % 20 == 0:
                    logger.info(f"Found {current_followers_count} followers so far ({len(self.followers_data)} processed)")
                    last_progress_log = current_followers_count
                
                # Process new followers
                if current_followers_count > previously_loaded_followers:
                    # Process only the new followers
                    new_followers = follower_items[previously_loaded_followers:]
                    self._process_follower_items(new_followers)
                    
                    # Update the count of previously loaded followers
                    previously_loaded_followers = current_followers_count
                    
                    # Reset the no new followers counter
                    no_new_followers_count = 0
                    consecutive_same_count = 0
                    no_progress_count = 0
                    
                    # Save checkpoint every 100 new followers
                    if len(self.followers_data) % 100 == 0:
                        self._save_followers_data_checkpoint()
                else:
                    # No new followers loaded
                    no_new_followers_count += 1
                    
                    # If the count hasn't changed for several scrolls, we might be at the end
                    if current_followers_count == previously_loaded_followers:
                        consecutive_same_count += 1
                    else:
                        consecutive_same_count = 0
                    
                    if scroll_count % 10 == 0:
                        logger.info(f"No new followers loaded (attempt {no_new_followers_count}/10)")
                    
                    # Increased from 5 to 10 attempts before giving up
                    # Also increased from 10 to 15 consecutive same count checks
                    if no_new_followers_count >= 10 or consecutive_same_count >= 15:
                        logger.info(f"No new followers after multiple scroll attempts, assuming all followers loaded")
                        break
                
                # Check if we've collected enough followers
                if len(self.followers_data) >= max_followers_to_collect:
                    logger.info(f"Collected {len(self.followers_data)} followers, stopping scrolling")
                    break
                
                # Check if we've reached the end of the follower list
                if self._is_at_end_of_follower_list(follower_list):
                    logger.info("Detected end of follower list, stopping scrolling")
                    break
                
                # Try clicking "Load More" button if it exists
                if scroll_count % 5 == 0:  # Try every 5 scrolls
                    if self._try_click_load_more_button(follower_list):
                        logger.info("Clicked 'Load More' button, waiting for new content")
                        self.human_behavior.random_sleep(2, 3)
                        # Reset counters since we've taken action
                        no_new_followers_count = 0
                        consecutive_same_count = 0
                        no_progress_count = 0
                        continue
                
                # Scroll the follower list
                try:
                    # Try different scrolling methods with more aggressive scrolling
                    scroll_attempts = 0
                    scroll_success = False
                    
                    # First, try a direct JavaScript approach that's more reliable for Instagram modals
                    try:
                        # This JavaScript finds the scrollable container in the modal and scrolls it
                        scroll_script = """
                            // Find all scrollable elements in the modal
                            var modal = document.querySelector('div[role="dialog"]');
                            if (!modal) return false;
                            
                            // Find all potentially scrollable elements
                            var scrollables = Array.from(modal.querySelectorAll('*')).filter(el => {
                                var style = window.getComputedStyle(el);
                                return (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                                       style.overflow === 'auto' || style.overflow === 'scroll') &&
                                       el.scrollHeight > el.clientHeight;
                            });
                            
                            // Sort by size (largest first)
                            scrollables.sort((a, b) => 
                                (b.offsetWidth * b.offsetHeight) - (a.offsetWidth * a.offsetHeight)
                            );
                            
                            // Try to scroll the largest scrollable element
                            if (scrollables.length > 0) {
                                var scrollable = scrollables[0];
                                var oldScrollTop = scrollable.scrollTop;
                                scrollable.scrollTop += 500; // Scroll down by 500px
                                return scrollable.scrollTop > oldScrollTop;
                            }
                            
                            return false;
                        """
                        
                        scroll_success = self.browser.execute_script(scroll_script)
                        if scroll_success:
                            logger.info("Successfully scrolled using direct JavaScript approach")
                        else:
                            logger.debug("Direct JavaScript scrolling didn't find a scrollable element")
                    except Exception as e:
                        logger.debug(f"Direct JavaScript scrolling failed: {str(e)}")
                    
                    # If direct JavaScript approach failed, try other methods
                    while scroll_attempts < 3 and not scroll_success:
                        try:
                            # Method 1: Scroll to a specific position
                            current_height = self.browser.execute_script("return arguments[0].scrollHeight", follower_list)
                            visible_height = self.browser.execute_script("return arguments[0].clientHeight", follower_list)
                            current_position = self.browser.execute_script("return arguments[0].scrollTop", follower_list)
                            
                            # Calculate new position (scroll down by 80% of the visible height)
                            new_position = current_position + (visible_height * 0.8)
                            
                            # Scroll to the new position
                            self.browser.execute_script(f"arguments[0].scrollTop = {new_position}", follower_list)
                            scroll_success = True
                        except:
                            scroll_attempts += 1
                            try:
                                # Method 2: Use JavaScript to scroll down by a fixed amount
                                self.browser.execute_script("arguments[0].scrollTop += 500", follower_list)
                                scroll_success = True
                            except:
                                scroll_attempts += 1
                                try:
                                    # Method 3: Use ActionChains to scroll
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    from selenium.webdriver.common.keys import Keys
                                    
                                    # Move to the follower list and press PAGE_DOWN
                                    ActionChains(self.browser).move_to_element(follower_list).send_keys(Keys.PAGE_DOWN).perform()
                                    scroll_success = True
                                except:
                                    scroll_attempts += 1
                    
                    if not scroll_success:
                        logger.warning("All scrolling methods failed, trying one last approach")
                        try:
                            # Method 4: Try to use JavaScript to scroll the dialog itself
                            self.browser.execute_script("""
                                var dialogs = document.querySelectorAll('div[role="dialog"]');
                                if (dialogs.length > 0) {
                                    // Find all scrollable elements in the dialog
                                    var scrollableElements = [];
                                    var allElements = dialogs[0].querySelectorAll('*');
                                    
                                    for (var i = 0; i < allElements.length; i++) {
                                        var element = allElements[i];
                                        var style = window.getComputedStyle(element);
                                        if (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                                            style.overflow === 'auto' || style.overflow === 'scroll') {
                                            
                                            // Only consider elements that are actually scrollable
                                            if (element.scrollHeight > element.clientHeight) {
                                                scrollableElements.push({
                                                    element: element,
                                                    size: element.offsetWidth * element.offsetHeight
                                                });
                                            }
                                        }
                                    }
                                    
                                    // Sort by size (largest first)
                                    scrollableElements.sort(function(a, b) {
                                        return b.size - a.size;
                                    });
                                    
                                    // Try to scroll each element, starting with the largest
                                    for (var j = 0; j < scrollableElements.length; j++) {
                                        var el = scrollableElements[j].element;
                                        var oldScrollTop = el.scrollTop;
                                        el.scrollTop += 500;
                                        
                                        // If we successfully scrolled, break the loop
                                        if (el.scrollTop > oldScrollTop) {
                                            break;
                                        }
                                    }
                                }
                            """)
                            logger.info("Applied JavaScript scrolling to dialog elements")
                            scroll_success = True
                        except Exception as e:
                            logger.warning(f"JavaScript dialog scrolling failed: {str(e)}")
                            
                            try:
                                # Method 5: Try to click on an element at the bottom of the list to force scrolling
                                follower_items = self._get_follower_items_from_container(follower_list)
                                if follower_items and len(follower_items) > 0:
                                    last_item = follower_items[-1]
                                    ActionChains(self.browser).move_to_element(last_item).perform()
                                    logger.info("Moved to last follower item to force scrolling")
                                    scroll_success = True
                            except Exception as e:
                                logger.warning(f"Last resort scrolling also failed: {str(e)}")
                                
                                # Final attempt: Try to use keyboard shortcuts directly on the document
                                try:
                                    ActionChains(self.browser).send_keys(Keys.PAGE_DOWN).perform()
                                    logger.info("Sent PAGE_DOWN key to document")
                                    scroll_success = True
                                except Exception as e:
                                    logger.warning(f"Keyboard shortcut scrolling failed: {str(e)}")
                
                except Exception as e:
                    logger.warning(f"Error scrolling: {str(e)}")
                
                # Wait for new content to load with random delay
                self.human_behavior.random_sleep(1, 2)  # Shorter delay to speed up collection
                
                # Check if we're making progress with scrolling
                is_making_progress, current_height, current_position = self._is_making_scrolling_progress(
                    follower_list, previous_height, previous_position)
                
                if not is_making_progress:
                    no_progress_count += 1
                    logger.debug(f"No scrolling progress detected (count: {no_progress_count}/3)")
                    
                    if no_progress_count >= 3:
                        # Try more aggressive scrolling methods
                        logger.info("No scrolling progress after multiple attempts, trying aggressive methods")
                        
                        try:
                            # Method 1: Scroll to bottom
                            self.browser.execute_script(
                                "arguments[0].scrollTop = arguments[0].scrollHeight", follower_list)
                            logger.debug("Applied aggressive scroll to bottom")
                        except Exception as e:
                            logger.debug(f"Aggressive scroll to bottom failed: {str(e)}")
                            
                            try:
                                # Method 2: Use keyboard shortcuts
                                from selenium.webdriver.common.action_chains import ActionChains
                                from selenium.webdriver.common.keys import Keys
                                
                                # Focus on the element and press End key
                                ActionChains(self.browser).move_to_element(follower_list).click().send_keys(Keys.END).perform()
                                logger.debug("Applied aggressive keyboard END key")
                            except Exception as e:
                                logger.debug(f"Aggressive keyboard END failed: {str(e)}")
                                
                                try:
                                    # Method 3: Click at the bottom of the container
                                    height = follower_list.size['height']
                                    ActionChains(self.browser).move_to_element_with_offset(
                                        follower_list, 10, height - 10).click().perform()
                                    logger.debug("Applied aggressive click at bottom")
                                except Exception as e:
                                    logger.debug(f"Aggressive click at bottom failed: {str(e)}")
                        
                        # Reset counter after aggressive attempts
                        no_progress_count = 0
                else:
                    # Reset counter if we're making progress
                    no_progress_count = 0
                
                # Update previous values for next comparison
                previous_height = current_height
                previous_position = current_position
                
                # Add some randomness to scrolling behavior
                if random.random() < 0.1:  # 10% chance to pause scrolling
                    logger.info("Taking a short break from scrolling")
                    self.human_behavior.random_sleep(2, 4)
            
            logger.info(f"Finished extracting followers. Total followers collected: {len(self.followers_data)}")
            
        except Exception as e:
            logger.error(f"Failed to extract followers: {str(e)}")
            # Check if browser window is closed
            if "no such window" in str(e).lower() or "window already closed" in str(e).lower():
                logger.error("Browser window was closed. Attempting to recover session.")
                self._recover_session()
    
    def _get_follower_items_from_container(self, container):
        """
        Extract follower items from the container.
        
        Args:
            container: The container element with follower items
            
        Returns:
            list: List of follower item elements
        """
        follower_items = []
        
        try:
            # Try different selectors for follower items
            item_selectors = [
                "li",  # Most common
                "div[role='button']",  # Another common pattern
                "div > div > div",  # Generic nested divs
                "a",  # Direct links
                "div.PZuss li",  # Specific Instagram class
                "div._aae- div",  # Another Instagram class
                # Add new selectors for the current Instagram UI
                "div._ab8w._ab94._ab97._ab9h._ab9k._ab9p._abcm",  # Current Instagram follower item class
                "div[role='dialog'] div[role='button']",  # Buttons in the dialog
                "div._aano div",  # Children of the scrollable container
                "div[role='dialog'] a",  # Links in the dialog
                "div._ab8w",  # Another Instagram class
                "div._ab8y",  # Another Instagram class
                "div._abm4"   # Another Instagram class
            ]
            
            for selector in item_selectors:
                try:
                    items = container.find_elements(By.CSS_SELECTOR, selector)
                    if items and len(items) > 0:
                        # Check if these items look like follower items (contain usernames or links)
                        valid_items = []
                        for item in items:
                            try:
                                # Check if item contains a link
                                links = item.find_elements(By.TAG_NAME, "a")
                                if links and len(links) > 0:
                                    for link in links:
                                        href = link.get_attribute("href")
                                        if href and "instagram.com/" in href and "/p/" not in href:
                                            valid_items.append(item)
                                            break
                            except:
                                continue
                        
                        if valid_items:
                            follower_items = valid_items
                            logger.info(f"Found {len(follower_items)} valid follower items with selector: {selector}")
                            break
                except Exception as e:
                    logger.debug(f"Error finding follower items with selector {selector}: {str(e)}")
                    continue
            
            # If we still don't have follower items, try a more generic approach
            if not follower_items:
                # Look for any elements that might be follower items
                try:
                    # Look for elements with links
                    links = container.find_elements(By.TAG_NAME, "a")
                    profile_links = []
                    
                    for link in links:
                        href = link.get_attribute("href")
                        if href and "/p/" not in href and "/explore/" not in href and "instagram.com/" in href:
                            # Find the parent element that might be the follower item
                            try:
                                parent = link
                                for _ in range(3):  # Go up to 3 levels up
                                    parent = parent.find_element(By.XPATH, "..")
                                    if parent.tag_name == "li" or parent.get_attribute("role") == "button":
                                        profile_links.append(parent)
                                        break
                            except:
                                # If we can't find a suitable parent, use the link itself
                                profile_links.append(link)
                    
                    if profile_links:
                        follower_items = profile_links
                        logger.info(f"Found {len(follower_items)} follower items from links")
                
                except Exception as e:
                    logger.warning(f"Error finding follower items from links: {str(e)}")
                
                # If we still don't have follower items, try one more approach
                if not follower_items:
                    try:
                        # Try to find any div elements that might be follower items
                        divs = container.find_elements(By.TAG_NAME, "div")
                        
                        # Filter divs that might be follower items (have a reasonable size and contain text)
                        potential_items = []
                        for div in divs:
                            try:
                                # Check if div has a reasonable size
                                size = div.size
                                if size['height'] > 30 and size['width'] > 100:  # Typical follower item size
                                    # Check if div contains text (username)
                                    text = div.text
                                    if text and len(text) > 0:
                                        # Check if div contains an image (profile picture)
                                        imgs = div.find_elements(By.TAG_NAME, "img")
                                        if imgs and len(imgs) > 0:
                                            potential_items.append(div)
                            except:
                                continue
                        
                        if potential_items:
                            follower_items = potential_items
                            logger.info(f"Found {len(follower_items)} potential follower items from divs")
                    except Exception as e:
                        logger.warning(f"Error finding follower items from divs: {str(e)}")
            
            # If we still don't have follower items, try a JavaScript approach
            if not follower_items:
                try:
                    # Use JavaScript to find potential follower items
                    follower_items_js = self.browser.execute_script("""
                        var container = arguments[0];
                        var potentialItems = [];
                        
                        // Function to check if an element might be a follower item
                        function isPotentialFollowerItem(element) {
                            // Check if it has a link to a profile
                            var links = element.querySelectorAll('a');
                            for (var i = 0; i < links.length; i++) {
                                var href = links[i].getAttribute('href');
                                if (href && href.includes('instagram.com/') && !href.includes('/p/')) {
                                    return true;
                                }
                            }
                            
                            // Check if it has an image (profile picture)
                            var imgs = element.querySelectorAll('img');
                            if (imgs.length > 0) {
                                // Check if it has text (username)
                                if (element.textContent && element.textContent.trim().length > 0) {
                                    return true;
                                }
                            }
                            
                            return false;
                        }
                        
                        // Find all divs in the container
                        var divs = container.querySelectorAll('div');
                        for (var i = 0; i < divs.length; i++) {
                            var div = divs[i];
                            if (isPotentialFollowerItem(div)) {
                                potentialItems.push(div);
                            }
                        }
                        
                        return potentialItems;
                    """, container)
                    
                    if follower_items_js and len(follower_items_js) > 0:
                        follower_items = follower_items_js
                        logger.info(f"Found {len(follower_items)} follower items using JavaScript")
                except Exception as e:
                    logger.warning(f"Error finding follower items with JavaScript: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Error getting follower items: {str(e)}")
        
        return follower_items
    
    def _process_follower_items(self, follower_items):
        """
        Process follower items to extract username, full name, and other data.
        
        Args:
            follower_items: List of follower item elements
        """
        processed_count = 0
        
        for item in follower_items:
            try:
                # Extract data from the follower item
                username = None
                full_name = None
                profile_pic_url = None
                is_verified = False
                
                # Try multiple approaches to extract the username
                
                # Approach 1: Look for links with username
                links = item.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        if href and "instagram.com/" in href:
                            # Extract username from the URL
                            username_match = re.search(r'instagram\.com/([^/]+)/?', href)
                            if username_match:
                                potential_username = username_match.group(1)
                                # Validate username (exclude explore, p, stories, etc.)
                                if (potential_username and 
                                    potential_username not in ["explore", "p", "stories", "direct", "reels"] and
                                    not potential_username.startswith("p/")):
                                    username = potential_username
                                    break
                    except:
                        continue
                
                # Approach 2: Look for elements with specific attributes
                if not username:
                    username_elements = item.find_elements(By.CSS_SELECTOR, 
                        "span[title], div[title], span._aacl, div._aacl, span._ap3a, div._ap3a")
                    
                    for element in username_elements:
                        try:
                            text = element.text.strip()
                            if text and self._is_valid_instagram_username(text):
                                username = text
                                break
                        except:
                            continue
                
                # Approach 3: Look for elements with specific classes that might contain the username
                if not username:
                    potential_elements = item.find_elements(By.CSS_SELECTOR, 
                        "div > div > div > div > span, div > div > span, div > span")
                    
                    for element in potential_elements:
                        try:
                            text = element.text.strip()
                            if text and self._is_valid_instagram_username(text):
                                username = text
                                break
                        except:
                            continue
                
                # Extract full name
                try:
                    # Try to find elements that might contain the full name
                    name_elements = item.find_elements(By.CSS_SELECTOR, 
                        "div > div > div > div:nth-child(2), span + span, div + div > span, div._aade, span._aade")
                    
                    for element in name_elements:
                        try:
                            text = element.text.strip()
                            if text and text != username:
                                full_name = text
                                break
                        except:
                            continue
                    
                    # If we still don't have a full name, try to get all text from the item
                    if not full_name:
                        full_text = item.text.strip()
                        if full_text and username and username in full_text:
                            # Extract text that might be the full name
                            remaining_text = full_text.replace(username, "").strip()
                            if remaining_text:
                                full_name = remaining_text
                except:
                    pass
                
                # Extract profile picture URL
                try:
                    img_elements = item.find_elements(By.TAG_NAME, "img")
                    for img in img_elements:
                        src = img.get_attribute("src")
                        if src and ("instagram.com" in src or "cdninstagram.com" in src):
                            profile_pic_url = src
                            break
                except:
                    pass
                
                # Check if verified
                try:
                    verified_badges = item.find_elements(By.CSS_SELECTOR, 
                        "span[aria-label='Verified'], span[title='Verified'], svg[aria-label='Verified']")
                    is_verified = len(verified_badges) > 0
                except:
                    pass
                
                # Skip if no username was found
                if not username:
                    continue
                
                # Add to followers data
                follower_data = {
                    "username": username,
                    "full_name": full_name if full_name else "",
                    "profile_pic_url": profile_pic_url if profile_pic_url else "",
                    "is_verified": is_verified,
                    "scraped_at": datetime.now().isoformat(),
                    "detailed_profile_analyzed": False
                }
                
                # Check if this follower is already in our list
                if not any(f.get("username") == username for f in self.followers_data):
                    self.followers_data.append(follower_data)
                
                processed_count += 1
                
                # Log progress periodically
                if processed_count % 10 == 0:
                    logger.info(f"Processed {processed_count} followers")
                
            except Exception as e:
                logger.warning(f"Error processing follower item: {str(e)}")
                continue
        
        return processed_count
    
    def _extract_followers_directly(self):
        """
        Extract followers directly from the page when the follower list container cannot be found.
        """
        logger.info("Attempting to extract followers directly from the page")
        
        try:
            # Look for any links that might be profile links
            all_links = self.browser.find_elements(By.TAG_NAME, "a")
            profile_links = []
            
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    if href and "/p/" not in href and "/explore/" not in href and "instagram.com/" in href:
                        username = href.split("/")[-2] if href.endswith("/") else href.split("/")[-1]
                        if username and username != self.target_username:
                            profile_links.append((link, username))
                except:
                    continue
            
            logger.info(f"Found {len(profile_links)} potential profile links")
            
            # Process these links directly
            for link, username in profile_links[:100]:  # Limit to 100 to avoid processing too many
                try:
                    # Skip if already processed
                    if username in [f["username"] for f in self.followers_data]:
                        continue
                    
                    # Try to get the parent element to extract more information
                    parent = link
                    try:
                        for _ in range(3):  # Go up to 3 levels
                            parent = parent.find_element(By.XPATH, "..")
                    except:
                        pass
                    
                    # Extract full name
                    fullname = ""
                    try:
                        name_elements = parent.find_elements(By.CSS_SELECTOR, "span, div")
                        for element in name_elements:
                            text = element.text
                            if text and text != username and " " in text:
                                fullname = text
                                break
                    except:
                        pass
                    
                    # Extract profile picture
                    profile_pic_url = ""
                    try:
                        img_elements = parent.find_elements(By.TAG_NAME, "img")
                        for img in img_elements:
                            src = img.get_attribute("src")
                            if src and ("profile_pic" in src or "instagram" in src):
                                profile_pic_url = src
                                break
                    except:
                        pass
                    
                    # Check if verified
                    is_verified = False
                    try:
                        verified_badges = parent.find_elements(By.CSS_SELECTOR, "span[aria-label*='Verified']")
                        is_verified = len(verified_badges) > 0
                    except:
                        pass
                    
                    # Create follower data
                    follower_data = {
                        "username": username,
                        "fullname": fullname,
                        "profile_pic_url": profile_pic_url,
                        "is_verified": is_verified,
                        "collected_at": datetime.now().isoformat(),
                        "detailed_profile_analyzed": False
                    }
                    
                    self.followers_data.append(follower_data)
                    
                except Exception as e:
                    logger.debug(f"Error processing profile link: {str(e)}")
                    continue
            
            if self.followers_data:
                logger.info(f"Collected {len(self.followers_data)} followers from profile links")
                return True
            else:
                logger.warning("Could not collect any followers directly from the page")
                return False
                
        except Exception as e:
            logger.error(f"Error extracting followers directly: {str(e)}")
            return False
    
    def _recover_session(self):
        """
        Attempt to recover the session after a browser window closure.
        """
        try:
            logger.info("Attempting to recover session after browser window closure")
            
            # Close the current browser if it exists
            try:
                if self.browser:
                    self.browser.quit()
            except:
                pass
            
            # Restart the browser
            logger.info("Restarting browser")
            self.browser = setup_browser(
                headless=self.config.get("headless", False),
                proxy=self.current_proxy
            )
            
            # Log in again
            self._login()
            
            # Navigate back to the profile
            self._navigate_to_profile()
            
            logger.info("Session recovered successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to recover session: {str(e)}")
            return False
    
    def _is_challenge_present(self):
        """
        Check if Instagram is presenting a challenge or captcha.
        
        Returns:
            bool: True if a challenge is detected, False otherwise
        """
        try:
            # Check for common challenge indicators
            challenge_indicators = [
                "//div[contains(text(), 'Please Wait')]",
                "//div[contains(text(), 'Suspicious Login Attempt')]",
                "//div[contains(text(), 'We detected an unusual login attempt')]",
                "//div[contains(text(), 'Enter the code we sent to')]",
                "//div[contains(text(), 'Enter Security Code')]",
                "//div[contains(text(), 'Confirm it')]",
                "//div[contains(text(), 'captcha')]",
                "//div[contains(text(), 'Captcha')]",
                "//div[contains(text(), 'challenge')]",
                "//div[contains(text(), 'Challenge')]",
                "//div[contains(text(), 'unusual activity')]",
                "//div[contains(text(), 'Unusual Activity')]"
            ]
            
            for indicator in challenge_indicators:
                try:
                    element = self.browser.find_element(By.XPATH, indicator)
                    if element and element.is_displayed():
                        logger.warning(f"Challenge detected: {element.text}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking for challenges: {str(e)}")
            return False
    
    @log_execution_time
    def analyze_follower_profiles(self):
        """
        Navigate to individual follower profiles and collect detailed information.
        Only analyzes a subset of followers to avoid rate limiting.
        """
        # Limit the number of profiles to analyze to avoid rate limiting
        max_profiles_to_analyze = min(20, len(self.followers_data))
        
        logger.info(f"Analyzing {max_profiles_to_analyze} follower profiles in detail")
        
        analyzed_count = 0
        
        for follower in self.followers_data[:max_profiles_to_analyze]:
            try:
                # Skip if already analyzed
                if follower.get("detailed_profile_analyzed", False):
                    continue
                
                # Validate username - skip if it doesn't look like a valid Instagram username
                username = follower["username"]
                if not self._is_valid_instagram_username(username):
                    logger.warning(f"Skipping invalid username: {username}")
                    continue
                
                # Navigate to follower profile
                profile_url = PROFILE_URL.format(username)
                logger.info(f"Analyzing profile for {username}")
                
                self.navigate_to(profile_url)
                
                # Wait for profile to load
                try:
                    # Wait for profile stats to load
                    wait_for_element(self.browser, PROFILE_STATS, timeout=15)
                except TimeoutException:
                    logger.warning(f"Timeout waiting for profile stats for {username}")
                    continue
                
                # Extract profile statistics
                profile_stats = self._extract_profile_statistics_ui()
                if profile_stats:
                    follower.update(profile_stats)
                
                # Determine account type
                account_type = self._determine_account_type_ui()
                if account_type:
                    follower["account_type"] = account_type
                
                # Check if account is private
                is_private = self._is_account_private_ui()
                follower["is_private"] = is_private
                
                # Mark as analyzed
                follower["detailed_profile_analyzed"] = True
                analyzed_count += 1
                
                # Add random delay between profile visits
                self.human_behavior.random_sleep(2, 5)
                
            except Exception as e:
                logger.error(f"Error analyzing profile for {follower.get('username', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Analyzed {analyzed_count} follower profiles in detail")
    
    def _is_valid_instagram_username(self, username):
        """
        Check if a string looks like a valid Instagram username.
        
        Args:
            username: The username to validate
            
        Returns:
            bool: True if the username appears valid, False otherwise
        """
        # Skip usernames that are clearly not valid
        if not username or len(username) < 3:
            return False
            
        # Skip usernames that contain URL parameters or special characters
        if any(char in username for char in ['?', '&', '=', '/', '.', ' ']):
            return False
            
        # Skip common navigation elements that might be mistaken for usernames
        invalid_usernames = [
            'login', 'signup', 'explore', 'about', 'press', 'api', 'jobs', 'privacy', 
            'terms', 'hashtag', 'locations', 'accounts', 'emailsignup', 'next', 'previous',
            'direct', 'inbox', 'activity', 'settings', 'help', 'support'
        ]
        
        if username.lower() in invalid_usernames:
            return False
            
        # Basic regex pattern for Instagram usernames (letters, numbers, underscores, periods)
        import re
        pattern = r'^[a-zA-Z0-9_.]{1,30}$'
        return bool(re.match(pattern, username))
    
    def _extract_profile_statistics_ui(self):
        """
        Extract profile statistics using UI scraping.
        
        Returns:
            Dictionary with profile statistics
        """
        stats = {"posts": 0, "followers": 0, "following": 0}
        
        try:
            # Find the stats container
            stats_container = wait_for_element(self.browser, PROFILE_STATS, timeout=5)
            
            if not stats_container:
                return stats
            
            # Extract posts count
            try:
                posts_element = wait_for_element(self.browser, PROFILE_POSTS_COUNT, timeout=3)
                if posts_element:
                    posts_text = posts_element.text.split()[0]
                    
                    # Convert to integer
                    if "K" in posts_text:
                        stats["posts"] = int(float(posts_text.replace("K", "")) * 1000)
                    elif "M" in posts_text:
                        stats["posts"] = int(float(posts_text.replace("M", "")) * 1000000)
                    else:
                        stats["posts"] = int(posts_text.replace(",", ""))
            except Exception:
                pass
            
            # Extract followers count
            try:
                followers_element = wait_for_element(self.browser, PROFILE_FOLLOWERS_COUNT, timeout=3)
                if followers_element:
                    followers_text = followers_element.text.split()[0]
                    
                    # Convert to integer
                    if "K" in followers_text:
                        stats["followers"] = int(float(followers_text.replace("K", "")) * 1000)
                    elif "M" in followers_text:
                        stats["followers"] = int(float(followers_text.replace("M", "")) * 1000000)
                    else:
                        stats["followers"] = int(followers_text.replace(",", ""))
            except Exception:
                pass
            
            # Extract following count
            try:
                following_element = wait_for_element(self.browser, PROFILE_FOLLOWING_COUNT, timeout=3)
                if following_element:
                    following_text = following_element.text.split()[0]
                    
                    # Convert to integer
                    if "K" in following_text:
                        stats["following"] = int(float(following_text.replace("K", "")) * 1000)
                    elif "M" in following_text:
                        stats["following"] = int(float(following_text.replace("M", "")) * 1000000)
                    else:
                        stats["following"] = int(following_text.replace(",", ""))
            except Exception:
                pass
            
            return stats
            
        except Exception as e:
            logger.debug(f"Error extracting profile statistics: {str(e)}")
            return stats
    
    def _determine_account_type_ui(self):
        """
        Determine account type using UI scraping.
        
        Returns:
            String account type: "personal", "business", "creator", or "unknown"
        """
        try:
            # Check for business/creator badge
            badges = self.browser.find_elements(By.CSS_SELECTOR, ACCOUNT_TYPE_BADGE)
            
            for badge in badges:
                badge_text = badge.text.lower()
                
                if "business" in badge_text:
                    return "business"
                elif "creator" in badge_text:
                    return "creator"
            
            # If no badge found, assume personal account
            return "personal"
            
        except Exception as e:
            logger.debug(f"Error determining account type: {str(e)}")
            return "unknown"
    
    def _is_account_private_ui(self):
        """
        Check if account is private using UI scraping.
        
        Returns:
            Boolean indicating if the account is private
        """
        try:
            # Look for private account indicator
            private_indicators = self.browser.find_elements(By.CSS_SELECTOR, PRIVATE_ACCOUNT_INDICATOR)
            
            for indicator in private_indicators:
                if "private" in indicator.text.lower():
                    return True
            
            # Also check the page source for private account indicators
            page_source = self.browser.page_source
            if '"is_private":true' in page_source or 'This Account is Private' in page_source:
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking if account is private: {str(e)}")
            return False
    
    def save_follower_data(self):
        """Save the collected follower data to a JSON file."""
        if not self.followers_data:
            logger.warning("No follower data to save")
            return
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.target_username}_followers_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        # Save to JSON file
        with open(filepath, "w") as f:
            json.dump({
                "target_username": self.target_username,
                "collection_timestamp": datetime.now().isoformat(),
                "total_followers_collected": len(self.followers_data),
                "followers": self.followers_data
            }, f, indent=2)
        
        logger.info(f"Follower data saved to {filepath}")
        
        # Also save a categorized version
        self.categorize_and_save_followers()
    
    def categorize_and_save_followers(self):
        """
        Categorize followers based on preliminary metrics and save to a separate file.
        """
        if not self.followers_data:
            return
        
        # Initialize categories
        categories = {
            "potential_bots": [],
            "business_accounts": [],
            "creator_accounts": [],
            "private_accounts": [],
            "public_personal_accounts": [],
            "high_follower_accounts": [],
            "low_engagement_potential": []
        }
        
        # Categorize followers
        for follower in self.followers_data:
            # Skip followers without detailed analysis
            if not follower.get("detailed_profile_analyzed", False):
                continue
            
            # Check for potential bots based on username patterns
            username = follower["username"].lower()
            if (
                any(pattern in username for pattern in ["bot", "follow", "gram", "like"]) or
                (username.isalnum() and len(username) >= 10 and any(c.isdigit() for c in username))
            ):
                categories["potential_bots"].append(follower["username"])
            
            # Categorize by account type
            account_type = follower.get("account_type", "unknown")
            if account_type == "business":
                categories["business_accounts"].append(follower["username"])
            elif account_type == "creator":
                categories["creator_accounts"].append(follower["username"])
            
            # Categorize by privacy status
            if follower.get("is_private", False):
                categories["private_accounts"].append(follower["username"])
            elif account_type == "personal":
                categories["public_personal_accounts"].append(follower["username"])
            
            # Categorize by follower count
            if follower.get("followers_count", 0) > 10000:
                categories["high_follower_accounts"].append(follower["username"])
            
            # Identify potential low engagement accounts
            following_count = follower.get("following_count", 0)
            followers_count = follower.get("followers_count", 0)
            posts_count = follower.get("posts_count", 0)
            
            if (
                following_count > 1000 and 
                (followers_count < 100 or (following_count / max(followers_count, 1)) > 10) and
                posts_count < 10
            ):
                categories["low_engagement_potential"].append(follower["username"])
        
        # Save categorized data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.target_username}_follower_categories_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump({
                "target_username": self.target_username,
                "categorization_timestamp": datetime.now().isoformat(),
                "categories": categories
            }, f, indent=2)
        
        logger.info(f"Categorized follower data saved to {filepath}")
    
    def _is_making_scrolling_progress(self, follower_list, previous_height, previous_position):
        """
        Check if we're making progress in scrolling by comparing heights and positions.
        
        Args:
            follower_list: The follower list container element
            previous_height: The previous scrollHeight of the container
            previous_position: The previous scrollTop position
            
        Returns:
            tuple: (is_making_progress, current_height, current_position)
        """
        try:
            # Get current scroll height and position
            current_height = self.browser.execute_script("return arguments[0].scrollHeight", follower_list)
            current_position = self.browser.execute_script("return arguments[0].scrollTop", follower_list)
            
            # Check if height has increased (new content loaded)
            height_increased = current_height > previous_height
            
            # Check if position has changed (scrolling occurred)
            position_changed = abs(current_position - previous_position) > 10
            
            # Log debug information
            if height_increased:
                logger.debug(f"Scroll height increased: {previous_height} -> {current_height} (+{current_height - previous_height}px)")
            
            if position_changed:
                logger.debug(f"Scroll position changed: {previous_position} -> {current_position}")
            
            # We're making progress if either height increased or position changed significantly
            is_making_progress = height_increased or position_changed
            
            return is_making_progress, current_height, current_position
            
        except Exception as e:
            logger.warning(f"Error checking scroll progress: {str(e)}")
            return False, previous_height, previous_position
    
    def _is_at_end_of_follower_list(self, follower_list):
        """
        Check if we've reached the end of the follower list by looking for end indicators.
        
        Args:
            follower_list: The follower list container element
            
        Returns:
            bool: True if we've reached the end, False otherwise
        """
        try:
            # First, try a direct JavaScript approach to check if we're at the bottom
            try:
                is_at_bottom = self.browser.execute_script("""
                    // Find the modal dialog
                    var modal = document.querySelector('div[role="dialog"]');
                    if (!modal) return false;
                    
                    // Find all scrollable elements in the modal
                    var scrollables = Array.from(modal.querySelectorAll('*')).filter(el => {
                        var style = window.getComputedStyle(el);
                        return (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                               style.overflow === 'auto' || style.overflow === 'scroll') &&
                               el.scrollHeight > el.clientHeight;
                    });
                    
                    // Sort by size (largest first) as the main container is usually the largest
                    scrollables.sort((a, b) => 
                        (b.offsetWidth * b.offsetHeight) - (a.offsetWidth * a.offsetHeight)
                    );
                    
                    // Check if we're at the bottom of the largest scrollable element
                    if (scrollables.length > 0) {
                        var scrollable = scrollables[0];
                        
                        // Check if we're at the bottom (with a small margin of error)
                        var atBottom = Math.abs((scrollable.scrollHeight - scrollable.scrollTop) - scrollable.clientHeight) < 5;
                        
                        // Also check if there's a loading indicator
                        var loadingIndicator = modal.querySelector('circle[role="progressbar"], svg[aria-label="Loading..."]');
                        var hasActiveLoader = loadingIndicator && window.getComputedStyle(loadingIndicator).display !== 'none';
                        
                        // If we're at the bottom and there's no active loader, we're likely at the end
                        return atBottom && !hasActiveLoader;
                    }
                    
                    return false;
                """)
                
                if is_at_bottom:
                    logger.info("JavaScript detection confirms we're at the bottom of the scrollable container")
                    return True
            except Exception as e:
                logger.debug(f"JavaScript end detection failed: {str(e)}")
            
            # Check for common end-of-list indicators
            
            # 1. Check if a loading spinner exists but is not visible (finished loading)
            spinners = self.browser.find_elements(By.CSS_SELECTOR, 
                "div[role='dialog'] circle, div[role='dialog'] svg[aria-label='Loading...'], div.W1Bne, " + 
                "svg[aria-label='Loading'], div.By4nA, circle[role='progressbar']")
            
            if spinners:
                for spinner in spinners:
                    try:
                        if not spinner.is_displayed():
                            logger.info("Found hidden loading spinner, indicating end of list")
                            return True
                    except:
                        pass
            
            # 2. Check for "Suggested" section that appears at the end of follower lists
            suggested_headers = self.browser.find_elements(By.XPATH, 
                "//*[contains(text(), 'Suggested') or contains(text(), 'Disarankan') or " +
                "contains(text(), 'Saran') or contains(text(), 'Recommended') or " +
                "contains(text(), 'People you might know') or contains(text(), 'Orang yang mungkin Anda kenal')]")
            
            if suggested_headers:
                for header in suggested_headers:
                    try:
                        if header.is_displayed():
                            logger.info(f"Found '{header.text}' section, indicating end of list")
                            return True
                    except:
                        pass
            
            # 3. Check for "See All Suggestions" button at the end
            see_all_buttons = self.browser.find_elements(By.XPATH, 
                "//*[contains(text(), 'See All') or contains(text(), 'Lihat Semua') or " +
                "contains(text(), 'View All') or contains(text(), 'Show All') or " +
                "contains(text(), 'See More') or contains(text(), 'Lihat Lainnya')]")
            
            if see_all_buttons:
                for button in see_all_buttons:
                    try:
                        if button.is_displayed():
                            logger.info(f"Found '{button.text}' button, indicating end of list")
                            return True
                    except:
                        pass
            
            # 4. Check if we've reached the bottom of the scrollable container
            try:
                # First try with the provided follower_list element
                scroll_height = self.browser.execute_script("return arguments[0].scrollHeight", follower_list)
                scroll_top = self.browser.execute_script("return arguments[0].scrollTop", follower_list)
                client_height = self.browser.execute_script("return arguments[0].clientHeight", follower_list)
                
                # If we're at the bottom of the container (with a small margin of error)
                if scroll_top + client_height >= scroll_height - 10:
                    # Double-check by trying to scroll a bit more
                    old_scroll_top = scroll_top
                    self.browser.execute_script("arguments[0].scrollTop += 50", follower_list)
                    self.human_behavior.random_sleep(0.5, 1)
                    
                    # Check if the position changed
                    new_scroll_top = self.browser.execute_script("return arguments[0].scrollTop", follower_list)
                    if new_scroll_top <= old_scroll_top + 10:  # If we didn't scroll much
                        logger.info("Reached bottom of scrollable container, indicating end of list")
                        return True
                
                # If that didn't work, try to find the scrollable element in the modal
                is_at_bottom = self.browser.execute_script("""
                    var modal = document.querySelector('div[role="dialog"]');
                    if (!modal) return false;
                    
                    var scrollables = Array.from(modal.querySelectorAll('*')).filter(el => {
                        var style = window.getComputedStyle(el);
                        return (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                               style.overflow === 'auto' || style.overflow === 'scroll') &&
                               el.scrollHeight > el.clientHeight;
                    });
                    
                    if (scrollables.length === 0) return false;
                    
                    // Check the largest scrollable element
                    var largest = scrollables.reduce((a, b) => 
                        (a.offsetWidth * a.offsetHeight > b.offsetWidth * b.offsetHeight) ? a : b
                    );
                    
                    // Try to scroll it a bit more
                    var oldScrollTop = largest.scrollTop;
                    largest.scrollTop += 50;
                    
                    // If we couldn't scroll further, we're at the bottom
                    return largest.scrollTop <= oldScrollTop + 10;
                """)
                
                if is_at_bottom:
                    logger.info("JavaScript check confirms we're at the bottom of the modal")
                    return True
                
            except Exception as e:
                logger.debug(f"Error checking scroll position: {str(e)}")
            
            # 5. Check for "End of Results" or similar messages
            end_messages = self.browser.find_elements(By.XPATH, 
                "//*[contains(text(), 'End of') or contains(text(), 'No more') or " +
                "contains(text(), 'Akhir dari') or contains(text(), 'Tidak ada lagi') or " +
                "contains(text(), 'No additional') or contains(text(), 'That\'s all')]")
            
            if end_messages:
                for message in end_messages:
                    try:
                        if message.is_displayed():
                            logger.info(f"Found end message: '{message.text}', indicating end of list")
                            return True
                    except:
                        pass
            
            # 6. Check for empty space at the bottom of the list
            try:
                # Check if there's a large empty space at the bottom of the follower list
                empty_space_check = self.browser.execute_script("""
                    var modal = document.querySelector('div[role="dialog"]');
                    if (!modal) return false;
                    
                    var scrollable = Array.from(modal.querySelectorAll('*')).filter(el => {
                        var style = window.getComputedStyle(el);
                        return (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                               style.overflow === 'auto' || style.overflow === 'scroll') &&
                               el.scrollHeight > el.clientHeight;
                    }).sort((a, b) => 
                        (b.offsetWidth * b.offsetHeight) - (a.offsetWidth * a.offsetHeight)
                    )[0];
                    
                    if (!scrollable) return false;
                    
                    // Get all follower items
                    var items = scrollable.querySelectorAll('div[role="button"], a[href*="instagram.com/"]:not([href*="/p/"])');
                    if (items.length === 0) return false;
                    
                    // Get the last item
                    var lastItem = items[items.length - 1];
                    var lastItemRect = lastItem.getBoundingClientRect();
                    
                    // Check if there's a large gap between the last item and the bottom of the scrollable area
                    var scrollableRect = scrollable.getBoundingClientRect();
                    var emptySpaceHeight = scrollableRect.bottom - lastItemRect.bottom;
                    
                    // If there's a large empty space (more than 3x the average item height), we're likely at the end
                    var averageItemHeight = Array.from(items).reduce((sum, item) => sum + item.offsetHeight, 0) / items.length;
                    return emptySpaceHeight > averageItemHeight * 3;
                """)
                
                if empty_space_check:
                    logger.info("Detected large empty space at the bottom of the follower list, indicating end of list")
                    return True
            except Exception as e:
                logger.debug(f"Error checking for empty space: {str(e)}")
            
            # 7. Check if the follower count matches the number of items we've found
            # This is a more reliable check but requires knowing the total follower count
            try:
                follower_count_text = None
                follower_count_elements = self.browser.find_elements(By.XPATH, 
                    "//*[contains(text(), 'follower') or contains(text(), 'pengikut')]")
                
                for element in follower_count_elements:
                    try:
                        if element.is_displayed():
                            follower_count_text = element.text
                            break
                    except:
                        continue
                
                if follower_count_text:
                    # Extract the number from text like "1,234 followers" or "1.2K followers"
                    import re
                    count_match = re.search(r'([\d,\.]+)(?:K|M|rb|jt)?\s*(?:follower|pengikut)', follower_count_text)
                    if count_match:
                        count_str = count_match.group(1).replace(',', '').replace('.', '')
                        if 'K' in follower_count_text or 'rb' in follower_count_text:
                            follower_count = int(float(count_match.group(1).replace(',', '')) * 1000)
                        elif 'M' in follower_count_text or 'jt' in follower_count_text:
                            follower_count = int(float(count_match.group(1).replace(',', '')) * 1000000)
                        else:
                            follower_count = int(count_str)
                        
                        # Get the current number of items in the list
                        items_count = self.browser.execute_script("""
                            var modal = document.querySelector('div[role="dialog"]');
                            if (!modal) return 0;
                            
                            var scrollable = Array.from(modal.querySelectorAll('*')).filter(el => {
                                var style = window.getComputedStyle(el);
                                return (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                                       style.overflow === 'auto' || style.overflow === 'scroll') &&
                                       el.scrollHeight > el.clientHeight;
                            }).sort((a, b) => 
                                (b.offsetWidth * b.offsetHeight) - (a.offsetWidth * a.offsetHeight)
                            )[0];
                            
                            if (!scrollable) return 0;
                            
                            // Count follower items
                            var items = scrollable.querySelectorAll('div[role="button"], a[href*="instagram.com/"]:not([href*="/p/"])');
                            return items.length;
                        """)
                        
                        # If we've found at least 95% of the followers, consider it complete
                        # This accounts for potential discrepancies in the follower count
                        if items_count >= follower_count * 0.95:
                            logger.info(f"Found {items_count} items, which is ≥95% of the reported {follower_count} followers")
                            return True
            except Exception as e:
                logger.debug(f"Error checking follower count: {str(e)}")
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking for end of follower list: {str(e)}")
            return False
    
    def _try_click_load_more_button(self, follower_list):
        """
        Try to find and click a "Load More" or "Show More" button if it exists.
        
        Args:
            follower_list: The follower list container element
            
        Returns:
            bool: True if a button was found and clicked, False otherwise
        """
        try:
            # Look for various "load more" button patterns
            load_more_selectors = [
                "button[type='button']",
                "a[role='button']",
                "div[role='button']",
                "span[role='button']",
                "button.sqdOP",  # Instagram-specific class
                "button._acan",  # Another Instagram class
                "button._acap",  # Another Instagram class
                "button._ab8w",  # Another Instagram class
                "button._ac7v",  # Another Instagram class
                "a.sqdOP",       # Instagram-specific class for links
                "div.sqdOP"      # Instagram-specific class for divs
            ]
            
            load_more_texts = [
                "Load more",
                "Show more",
                "See more",
                "View more",
                "More",
                "Load",
                "Muat lainnya",  # Indonesian
                "Lihat lainnya",  # Indonesian
                "Tampilkan lainnya",  # Indonesian
                "Lainnya",  # Indonesian
                "Muat lebih banyak"  # Indonesian
            ]
            
            # First try to find buttons with specific text
            for selector in load_more_selectors:
                elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        text = element.text.strip().lower()
                        if any(load_text.lower() in text for load_text in load_more_texts):
                            logger.info(f"Found load more button with text: {text}")
                            element.click()
                            self.human_behavior.random_sleep(1, 2)
                            return True
                    except:
                        continue
            
            # Try to find buttons by their aria-label
            aria_label_buttons = self.browser.find_elements(By.CSS_SELECTOR, "[aria-label]")
            for button in aria_label_buttons:
                try:
                    aria_label = button.get_attribute("aria-label").lower()
                    if any(load_text.lower() in aria_label for load_text in load_more_texts):
                        logger.info(f"Found load more button with aria-label: {aria_label}")
                        button.click()
                        self.human_behavior.random_sleep(1, 2)
                        return True
                except:
                    continue
            
            # Try to find any element at the bottom of the list that might be clickable
            try:
                # Get all elements in the follower list
                all_elements = follower_list.find_elements(By.XPATH, ".//*")
                
                # Filter to only visible elements near the bottom
                visible_elements = []
                for element in all_elements:
                    try:
                        if element.is_displayed():
                            # Get the element's position
                            location = element.location
                            if location and 'y' in location:
                                visible_elements.append((element, location['y']))
                    except:
                        continue
                
                # Sort by vertical position (y coordinate)
                visible_elements.sort(key=lambda x: x[1], reverse=True)
                
                # Try clicking the bottom-most elements that look like buttons
                for element, _ in visible_elements[:5]:  # Try the 5 bottom-most elements
                    try:
                        tag_name = element.tag_name.lower()
                        class_name = element.get_attribute("class") or ""
                        
                        # Check if it looks like a button
                        if (tag_name in ['button', 'a'] or 
                            'button' in class_name.lower() or 
                            element.get_attribute("role") == "button"):
                            
                            logger.info(f"Found potential load more button at bottom of list: {tag_name}.{class_name}")
                            element.click()
                            self.human_behavior.random_sleep(1, 2)
                            return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error finding bottom elements: {str(e)}")
            
            return False
            
        except Exception as e:
            logger.warning(f"Error trying to click load more button: {str(e)}")
            return False
    
    def _save_followers_data_checkpoint(self):
        """
        Save the current follower data to a checkpoint file to prevent data loss.
        """
        try:
            if not self.followers_data:
                logger.debug("No follower data to save for checkpoint")
                return
            
            # Create checkpoint directory if it doesn't exist
            checkpoint_dir = os.path.join("data", "followers", "checkpoints")
            os.makedirs(checkpoint_dir, exist_ok=True)
            
            # Create checkpoint filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_file = os.path.join(
                checkpoint_dir, 
                f"{self.target_username}_followers_checkpoint_{timestamp}.json"
            )
            
            # Save the data
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.followers_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Saved checkpoint with {len(self.followers_data)} followers to {checkpoint_file}")
            
        except Exception as e:
            logger.warning(f"Error saving follower data checkpoint: {str(e)}") 

    def _scroll_instagram_follower_modal(self):
        """
        Special method to handle scrolling in the Instagram follower modal.
        This method uses a more direct approach to find and scroll the modal.
        
        Returns:
            list: List of follower data dictionaries
        """
        logger.info("Using specialized method for Instagram follower modal scrolling")
        
        try:
            # Wait for the modal to appear
            self.human_behavior.random_sleep(2, 3)
            
            # Function to find the modal and container (reusable for refreshing)
            def find_modal_container():
                modal_script = """
                    // Find the follower modal
                    var modal = document.querySelector('div[role="dialog"]');
                    if (!modal) return {success: false, message: "No modal found"};
                    
                    // Find all elements that might contain follower items
                    var allElements = modal.querySelectorAll('*');
                    var followerContainers = [];
                    
                    // Find scrollable containers
                    var scrollables = Array.from(allElements).filter(el => {
                        var style = window.getComputedStyle(el);
                        return (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                               style.overflow === 'auto' || style.overflow === 'scroll') &&
                               el.scrollHeight > el.clientHeight;
                    });
                    
                    if (scrollables.length === 0) return {success: false, message: "No scrollable containers found"};
                    
                    // Sort by size (largest first) as the main container is usually the largest
                    scrollables.sort((a, b) => 
                        (b.offsetWidth * b.offsetHeight) - (a.offsetWidth * a.offsetHeight)
                    );
                    
                    var mainContainer = scrollables[0];
                    
                    // Find all elements that might be follower items
                    var potentialItems = Array.from(mainContainer.querySelectorAll('div[role="button"]'));
                    if (potentialItems.length === 0) {
                        potentialItems = Array.from(mainContainer.querySelectorAll('a')).filter(a => 
                            a.href && a.href.includes('instagram.com/') && !a.href.includes('/p/')
                        );
                    }
                    
                    if (potentialItems.length === 0) {
                        // Try a more generic approach
                        potentialItems = Array.from(mainContainer.querySelectorAll('div')).filter(div => {
                            var links = div.querySelectorAll('a');
                            for (var i = 0; i < links.length; i++) {
                                if (links[i].href && links[i].href.includes('instagram.com/') && !links[i].href.includes('/p/')) {
                                    return true;
                                }
                            }
                            return false;
                        });
                    }
                    
                    return {
                        success: true,
                        container: mainContainer,
                        items: potentialItems,
                        scrollHeight: mainContainer.scrollHeight,
                        clientHeight: mainContainer.clientHeight,
                        scrollTop: mainContainer.scrollTop
                    };
                """
                return self.browser.execute_script(modal_script)
            
            # Get initial modal info
            modal_info = find_modal_container()
            
            if not modal_info.get('success', False):
                logger.warning(f"Failed to find follower modal: {modal_info.get('message', 'Unknown error')}")
                return []
            
            logger.info(f"Found follower modal with {len(modal_info.get('items', []))} potential follower items")
            
            # Set up variables for scrolling
            followers_data = []
            max_scrolls = 2000  # Increased limit to collect more followers
            last_items_count = 0
            no_new_items_count = 0
            consecutive_same_height_count = 0
            last_scroll_height = 0
            bottom_detection_count = 0
            min_scrolls_before_stop = 50  # Minimum number of scrolls before allowing to stop
            stale_element_retries = 0
            max_stale_element_retries = 15  # Increased from 5 to 15
            consecutive_stale_element_errors = 0
            max_consecutive_stale_element_errors = 3
            page_refresh_attempts = 0
            max_page_refresh_attempts = 3
            last_checkpoint_time = time.time()
            checkpoint_interval = 60  # Save checkpoint every 60 seconds
            
            # Techniques to try when stuck
            scroll_techniques = [
                "normal",       # Regular scrolling
                "progressive",  # Gradually increasing scroll amounts
                "aggressive",   # Larger scroll jumps
                "bottom_jump",  # Jump to bottom
                "reset",        # Scroll back up then down
                "click_last",   # Click on last item
                "random_pause", # Add a longer random pause
                "micro_scroll"  # Very small incremental scrolls
            ]
            current_technique = "normal"
            technique_change_threshold = 3  # Change technique after this many attempts with no new items
            
            # Start scrolling loop
            for scroll_count in range(max_scrolls):
                try:
                    # Get current state
                    current_state = self.browser.execute_script("""
                        var container = arguments[0];
                        var items = container.querySelectorAll('div[role="button"]');
                        if (items.length === 0) {
                            items = container.querySelectorAll('a[href*="instagram.com/"]:not([href*="/p/"])');
                        }
                        
                        // Extract usernames from items
                        var usernames = [];
                        for (var i = 0; i < items.length; i++) {
                            var item = items[i];
                            var links = item.querySelectorAll('a');
                            for (var j = 0; j < links.length; j++) {
                                var href = links[j].href;
                                if (href && href.includes('instagram.com/') && !href.includes('/p/')) {
                                    var match = href.match(/instagram\\.com\\/([^\\/]+)\\/?/);
                                    if (match && match[1]) {
                                        usernames.push(match[1]);
                                        break;
                                    }
                                }
                            }
                        }
                        
                        return {
                            itemsCount: items.length,
                            scrollHeight: container.scrollHeight,
                            scrollTop: container.scrollTop,
                            clientHeight: container.clientHeight,
                            usernames: usernames
                        };
                    """, modal_info['container'])
                    
                    logger.info(f"Scroll {scroll_count + 1}: Found {current_state['itemsCount']} items, scrollTop: {current_state['scrollTop']}/{current_state['scrollHeight']}")
                    
                    # Reset consecutive stale element errors counter since we successfully executed JavaScript
                    consecutive_stale_element_errors = 0
                    
                    # Process new usernames
                    new_usernames = []
                    existing_usernames = [f.get('username') for f in followers_data]
                    
                    for username in current_state['usernames']:
                        if username not in existing_usernames and username not in new_usernames:
                            new_usernames.append(username)
                            followers_data.append({
                                'username': username,
                                'full_name': '',
                                'profile_pic_url': '',
                                'is_verified': False,
                                'scraped_at': datetime.now().isoformat(),
                                'detailed_profile_analyzed': False
                            })
                    
                    if new_usernames:
                        logger.info(f"Found {len(new_usernames)} new usernames: {', '.join(new_usernames[:5])}{' and more' if len(new_usernames) > 5 else ''}")
                        no_new_items_count = 0
                        bottom_detection_count = 0
                        current_technique = "normal"  # Reset to normal technique when finding new items
                        stale_element_retries = 0  # Reset stale element counter when finding new items
                    else:
                        no_new_items_count += 1
                        logger.info(f"No new usernames found (attempt {no_new_items_count}/20)")
                        
                        # Change technique if we're stuck
                        if no_new_items_count % technique_change_threshold == 0:
                            technique_index = (no_new_items_count // technique_change_threshold) % len(scroll_techniques)
                            current_technique = scroll_techniques[technique_index]
                            logger.info(f"Changing scroll technique to: {current_technique}")
                        
                        if no_new_items_count >= 20 and scroll_count > min_scrolls_before_stop:
                            # Before giving up, try one last page refresh
                            if page_refresh_attempts < max_page_refresh_attempts:
                                page_refresh_attempts += 1
                                logger.info(f"No new usernames after multiple scrolls, attempting page refresh ({page_refresh_attempts}/{max_page_refresh_attempts})")
                                
                                # Save current data before refresh
                                self.followers_data = followers_data
                                self._save_followers_data_checkpoint()
                                
                                # Refresh the page and navigate back to followers
                                current_url = self.browser.current_url
                                self.browser.refresh()
                                self.human_behavior.random_sleep(5, 7)
                                
                                # If we were on the followers page, navigate back to it
                                if "followers" in current_url:
                                    logger.info("Navigating back to followers page after refresh")
                                    self.browser.get(current_url)
                                    self.human_behavior.random_sleep(5, 7)
                                    
                                    # Try to click on followers count to reopen modal
                                    try:
                                        logger.info("Trying to click on followers count to reopen modal")
                                        follower_count_elements = self.browser.find_elements(By.XPATH, 
                                            "//*[contains(text(), 'follower') or contains(text(), 'pengikut')]")
                                        
                                        for element in follower_count_elements:
                                            try:
                                                if element.is_displayed():
                                                    logger.info(f"Found potential follower count element with text: {element.text}")
                                                    element.click()
                                                    self.human_behavior.random_sleep(3, 5)
                                                    break
                                            except:
                                                continue
                                    except Exception as e:
                                        logger.warning(f"Error clicking follower count after refresh: {str(e)}")
                                
                                # Get new modal container
                                self.human_behavior.random_sleep(3, 5)
                                new_modal_info = find_modal_container()
                                if new_modal_info.get('success', False):
                                    modal_info = new_modal_info
                                    logger.info("Successfully refreshed page and found new modal container")
                                    no_new_items_count = 0
                                    continue
                                else:
                                    logger.warning("Failed to find modal container after page refresh")
                            
                            logger.info("No new usernames after multiple scrolls and refresh attempts, stopping")
                            break
                    
                    # Check if scroll height has changed
                    if current_state['scrollHeight'] == last_scroll_height:
                        consecutive_same_height_count += 1
                        if consecutive_same_height_count >= 3:
                            logger.info("Scroll height not changing, trying to force load more content")
                            
                            # Try scrolling to the very bottom to trigger loading
                            self.browser.execute_script("""
                                var container = arguments[0];
                                container.scrollTop = container.scrollHeight;
                            """, modal_info['container'])
                            self.human_behavior.random_sleep(2, 3)
                            
                            # Try scrolling back up a bit and then down again (reset technique)
                            self.browser.execute_script("""
                                var container = arguments[0];
                                var currentPos = container.scrollTop;
                                container.scrollTop = Math.max(0, currentPos - 500);
                                setTimeout(function() {
                                    container.scrollTop = currentPos + 200;
                                }, 500);
                            """, modal_info['container'])
                            self.human_behavior.random_sleep(2, 3)
                            
                            # Try refreshing the modal container
                            logger.info("Refreshing modal container reference")
                            new_modal_info = find_modal_container()
                            if new_modal_info.get('success', False):
                                modal_info = new_modal_info
                                logger.info("Successfully refreshed modal container")
                            
                            consecutive_same_height_count = 0
                    else:
                        consecutive_same_height_count = 0
                    
                    last_scroll_height = current_state['scrollHeight']
                    
                    # Check if we're at the bottom
                    is_at_bottom = (current_state['scrollTop'] + current_state['clientHeight'] >= current_state['scrollHeight'] - 10)
                    
                    if is_at_bottom:
                        bottom_detection_count += 1
                        logger.info(f"Potentially at bottom of follower modal (detection {bottom_detection_count}/3)")
                        
                        if bottom_detection_count >= 3 and scroll_count > min_scrolls_before_stop:
                            # Try one more aggressive scroll to confirm
                            scroll_result = self.browser.execute_script("""
                                var container = arguments[0];
                                var oldScrollTop = container.scrollTop;
                                var oldScrollHeight = container.scrollHeight;
                                
                                // Try an aggressive scroll
                                container.scrollTop = container.scrollHeight + 1000;
                                
                                // Wait a bit for any dynamic loading
                                setTimeout(function() {}, 1000);
                                
                                return {
                                    didScroll: container.scrollTop > oldScrollTop + 10,
                                    newScrollHeight: container.scrollHeight,
                                    oldScrollHeight: oldScrollHeight
                                };
                            """, modal_info['container'])
                            
                            self.human_behavior.random_sleep(2, 3)
                            
                            # Try refreshing the modal container
                            logger.info("Refreshing modal container reference before final check")
                            new_modal_info = find_modal_container()
                            if new_modal_info.get('success', False):
                                modal_info = new_modal_info
                                logger.info("Successfully refreshed modal container")
                                
                                # Check if the height has changed after refresh
                                new_height = self.browser.execute_script("return arguments[0].scrollHeight", modal_info['container'])
                                if new_height > scroll_result['oldScrollHeight'] + 10:
                                    logger.info(f"Height increased after refresh: {scroll_result['oldScrollHeight']} -> {new_height}")
                                    bottom_detection_count = 0
                                    continue
                            
                            if not scroll_result['didScroll'] and scroll_result['newScrollHeight'] <= scroll_result['oldScrollHeight'] + 10:
                                logger.info("Confirmed at bottom of follower modal after multiple checks, stopping scrolling")
                                break
                            else:
                                logger.info("More content loaded after aggressive scroll, continuing")
                                bottom_detection_count = 0
                    
                    # Apply different scrolling techniques based on current_technique
                    if current_technique == "normal":
                        # Normal scrolling - 80% of visible height
                        scroll_amount = int(current_state['clientHeight'] * 0.8)
                        self.browser.execute_script(f"""
                            var container = arguments[0];
                            container.scrollTop += {scroll_amount};
                        """, modal_info['container'])
                    
                    elif current_technique == "progressive":
                        # Progressive scrolling - gradually increase scroll amount
                        base_amount = int(current_state['clientHeight'] * 0.5)
                        progressive_factor = min(2.0, 1.0 + (no_new_items_count * 0.1))
                        scroll_amount = int(base_amount * progressive_factor)
                        self.browser.execute_script(f"""
                            var container = arguments[0];
                            container.scrollTop += {scroll_amount};
                        """, modal_info['container'])
                        
                    elif current_technique == "aggressive":
                        # Aggressive scrolling - 120% of visible height
                        scroll_amount = int(current_state['clientHeight'] * 1.2)
                        self.browser.execute_script(f"""
                            var container = arguments[0];
                            container.scrollTop += {scroll_amount};
                        """, modal_info['container'])
                        
                    elif current_technique == "bottom_jump":
                        # Jump to bottom
                        self.browser.execute_script("""
                            var container = arguments[0];
                            container.scrollTop = container.scrollHeight;
                        """, modal_info['container'])
                        
                    elif current_technique == "reset":
                        # Scroll back up then down
                        self.browser.execute_script("""
                            var container = arguments[0];
                            var currentPos = container.scrollTop;
                            container.scrollTop = Math.max(0, currentPos - 800);
                            setTimeout(function() {
                                container.scrollTop = currentPos + 400;
                            }, 700);
                        """, modal_info['container'])
                        
                    elif current_technique == "click_last":
                        # Try to click on the last visible item
                        try:
                            self.browser.execute_script("""
                                var container = arguments[0];
                                var items = container.querySelectorAll('div[role="button"]');
                                if (items.length === 0) {
                                    items = container.querySelectorAll('a[href*="instagram.com/"]:not([href*="/p/"])');
                                }
                                
                                if (items.length > 0) {
                                    var lastVisibleIndex = 0;
                                    for (var i = items.length - 1; i >= 0; i--) {
                                        var rect = items[i].getBoundingClientRect();
                                        if (rect.top < window.innerHeight && rect.bottom > 0) {
                                            lastVisibleIndex = i;
                                            break;
                                        }
                                    }
                                    items[lastVisibleIndex].click();
                                    setTimeout(function() {
                                        // Click back on the container to regain focus
                                        container.click();
                                    }, 300);
                                }
                            """, modal_info['container'])
                            
                            # Then scroll normally
                            self.browser.execute_script(f"""
                                var container = arguments[0];
                                container.scrollTop += {int(current_state['clientHeight'] * 0.5)};
                            """, modal_info['container'])
                        except:
                            # If clicking fails, fall back to normal scrolling
                            self.browser.execute_script(f"""
                                var container = arguments[0];
                                container.scrollTop += {int(current_state['clientHeight'] * 0.8)};
                            """, modal_info['container'])
                    
                    elif current_technique == "random_pause":
                        # Normal scroll with a longer pause
                        scroll_amount = int(current_state['clientHeight'] * 0.8)
                        self.browser.execute_script(f"""
                            var container = arguments[0];
                            container.scrollTop += {scroll_amount};
                        """, modal_info['container'])
                        self.human_behavior.random_sleep(3, 5)  # Longer pause
                    
                    elif current_technique == "micro_scroll":
                        # Multiple small scrolls with pauses
                        micro_amount = int(current_state['clientHeight'] * 0.2)
                        for _ in range(4):
                            self.browser.execute_script(f"""
                                var container = arguments[0];
                                container.scrollTop += {micro_amount};
                            """, modal_info['container'])
                            self.human_behavior.random_sleep(0.5, 1)
                    
                    # Wait for new content to load - variable wait time
                    if current_technique == "random_pause" or current_technique == "micro_scroll":
                        # Already paused above
                        pass
                    else:
                        # Normal wait time
                        self.human_behavior.random_sleep(1.5, 2.5)
                    
                    # Save checkpoint periodically
                    current_time = time.time()
                    if current_time - last_checkpoint_time > checkpoint_interval:
                        logger.info(f"Saving checkpoint after {scroll_count} scrolls with {len(followers_data)} followers")
                        self.followers_data = followers_data
                        self._save_followers_data_checkpoint()
                        last_checkpoint_time = current_time
                        
                        # Refresh the modal container reference periodically
                        logger.info("Refreshing modal container reference")
                        new_modal_info = find_modal_container()
                        if new_modal_info.get('success', False):
                            modal_info = new_modal_info
                            logger.info("Successfully refreshed modal container")
                
                except Exception as e:
                    if "stale element reference" in str(e):
                        stale_element_retries += 1
                        consecutive_stale_element_errors += 1
                        logger.warning(f"Stale element reference encountered (retry {stale_element_retries}/{max_stale_element_retries})")
                        
                        if stale_element_retries >= max_stale_element_retries:
                            logger.error(f"Too many stale element retries, stopping: {str(e)}")
                            break
                        
                        if consecutive_stale_element_errors >= max_consecutive_stale_element_errors:
                            # Multiple consecutive stale element errors - try page refresh
                            if page_refresh_attempts < max_page_refresh_attempts:
                                page_refresh_attempts += 1
                                logger.warning(f"Multiple consecutive stale element errors, attempting page refresh ({page_refresh_attempts}/{max_page_refresh_attempts})")
                                
                                # Save current data before refresh
                                self.followers_data = followers_data
                                self._save_followers_data_checkpoint()
                                
                                # Refresh the page and navigate back to followers
                                current_url = self.browser.current_url
                                self.browser.refresh()
                                self.human_behavior.random_sleep(5, 7)
                                
                                # If we were on the followers page, navigate back to it
                                if "followers" in current_url:
                                    logger.info("Navigating back to followers page after refresh")
                                    self.browser.get(current_url)
                                    self.human_behavior.random_sleep(5, 7)
                                    
                                    # Try to click on followers count to reopen modal
                                    try:
                                        logger.info("Trying to click on followers count to reopen modal")
                                        follower_count_elements = self.browser.find_elements(By.XPATH, 
                                            "//*[contains(text(), 'follower') or contains(text(), 'pengikut')]")
                                        
                                        for element in follower_count_elements:
                                            try:
                                                if element.is_displayed():
                                                    logger.info(f"Found potential follower count element with text: {element.text}")
                                                    element.click()
                                                    self.human_behavior.random_sleep(3, 5)
                                                    break
                                            except:
                                                continue
                                    except Exception as e:
                                        logger.warning(f"Error clicking follower count after refresh: {str(e)}")
                                
                                # Get new modal container
                                self.human_behavior.random_sleep(3, 5)
                                new_modal_info = find_modal_container()
                                if new_modal_info.get('success', False):
                                    modal_info = new_modal_info
                                    logger.info("Successfully refreshed page and found new modal container")
                                    consecutive_stale_element_errors = 0
                                    continue
                                else:
                                    logger.warning("Failed to find modal container after page refresh")
                        
                        # Try to refresh the modal container
                        logger.info("Attempting to refresh modal container after stale element error")
                        self.human_behavior.random_sleep(2, 3)
                        
                        new_modal_info = find_modal_container()
                        if new_modal_info.get('success', False):
                            modal_info = new_modal_info
                            logger.info("Successfully refreshed modal container after stale element error")
                            consecutive_stale_element_errors = 0
                        else:
                            logger.warning("Failed to refresh modal container after stale element error")
                    else:
                        logger.error(f"Error during scrolling: {str(e)}")
                        # Save data before potentially breaking
                        if followers_data:
                            logger.info(f"Saving data after error with {len(followers_data)} followers")
                            self.followers_data = followers_data
                            self._save_followers_data_checkpoint()
                        break
            
            logger.info(f"Finished scrolling follower modal, collected {len(followers_data)} followers")
            
            # Update the main followers_data list
            self.followers_data = followers_data
            
            return followers_data
            
        except Exception as e:
            logger.error(f"Error in specialized follower modal scrolling: {str(e)}")
            return []
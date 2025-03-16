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
        os.makedirs(self.data_dir, exist_ok=True)
    
    def run(self):
        """
        Main method to run the follower scraper.
        
        Returns:
            List of follower data dictionaries
        """
        logger.info("Starting follower data collection")
        
        try:
            # Start the browser
            session_loaded = self.start()
            
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
            
            # Analyze follower profiles (only a subset to avoid rate limiting)
            self.analyze_follower_profiles()
            
            # Save the data
            self.save_follower_data()
            
            logger.info(f"Follower data collection completed. Collected {len(self.followers_data)} followers.")
            return self.followers_data
            
        except Exception as e:
            logger.error(f"Follower scraping failed: {str(e)}")
            raise
        finally:
            # Stop the browser
            self.stop()
    
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
                "div[aria-label*='Pengikut']"  # Indonesian language
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
                        "//*[contains(@style, 'overflow') or contains(@style, 'scroll')]")
                    
                    logger.info(f"Found {len(scrollable_elements)} potentially scrollable elements")
                    
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
                except Exception as e:
                    logger.warning(f"Error in dynamic follower list search: {str(e)}")
            
            # If we still don't have a follower list, try one more approach
            if not follower_list:
                logger.info("Trying to find any element that might contain the follower list")
                try:
                    # Look for any element that might contain the follower list
                    potential_containers = self.browser.find_elements(By.CSS_SELECTOR, "div[role='dialog'] div")
                    
                    for container in potential_containers:
                        try:
                            # Check if this container has multiple child elements that might be follower items
                            children = container.find_elements(By.XPATH, "./div")
                            if len(children) > 5:  # Assume it might be a list if it has several children
                                # Check if any of these children contain links
                                has_links = False
                                for child in children[:5]:  # Check first few children
                                    links = child.find_elements(By.TAG_NAME, "a")
                                    if links:
                                        has_links = True
                                        break
                                
                                if has_links:
                                    logger.info(f"Found potential follower list container with {len(children)} children")
                                    follower_list = container
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Error in container search: {str(e)}")
            
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
            
            # Set a reasonable limit for followers to collect
            max_followers_to_collect = min(follower_count if follower_count > 0 else 1000, 1000)
            logger.info(f"Will collect up to {max_followers_to_collect} followers")
            
            # Scroll to load followers
            previously_loaded_followers = 0
            no_new_followers_count = 0
            max_scrolls = 200  # Set a reasonable limit to avoid infinite scrolling
            
            for scroll_count in range(max_scrolls):
                logger.info(f"Scroll {scroll_count + 1}/{max_scrolls}")
                
                # Extract current followers before scrolling
                follower_items = self._get_follower_items_from_container(follower_list)
                current_followers_count = len(follower_items)
                
                logger.info(f"Found {current_followers_count} followers so far")
                
                # Process new followers
                if current_followers_count > previously_loaded_followers:
                    # Process only the new followers
                    new_followers = follower_items[previously_loaded_followers:]
                    self._process_follower_items(new_followers)
                    
                    # Update the count of previously loaded followers
                    previously_loaded_followers = current_followers_count
                    
                    # Reset the no new followers counter
                    no_new_followers_count = 0
                else:
                    # No new followers loaded
                    no_new_followers_count += 1
                    logger.info(f"No new followers loaded (attempt {no_new_followers_count}/3)")
                    
                    # If we've tried 3 times with no new followers, assume we've reached the end
                    if no_new_followers_count >= 3:
                        logger.info("No new followers after 3 scroll attempts, assuming all followers loaded")
                        break
                
                # Check if we've collected enough followers
                if len(self.followers_data) >= max_followers_to_collect:
                    logger.info(f"Collected {len(self.followers_data)} followers, stopping scrolling")
                    break
                
                # Scroll the follower list
                try:
                    # Try different scrolling methods
                    try:
                        # Method 1: Use JavaScript to scroll
                        self.browser.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", follower_list)
                    except:
                        try:
                            # Method 2: Alternative JavaScript scrolling
                            self.browser.execute_script(
                                "arguments[0].scrollTo(0, arguments[0].scrollHeight)", follower_list)
                        except:
                            try:
                                # Method 3: Use ActionChains to scroll
                                from selenium.webdriver.common.action_chains import ActionChains
                                from selenium.webdriver.common.keys import Keys
                                
                                # Move to the follower list and press PAGE_DOWN
                                ActionChains(self.browser).move_to_element(follower_list).send_keys(Keys.PAGE_DOWN).perform()
                            except Exception as e:
                                logger.warning(f"All scrolling methods failed: {str(e)}")
                except Exception as e:
                    logger.warning(f"Error scrolling: {str(e)}")
                
                # Wait for new content to load with random delay
                self.human_behavior.random_sleep(2, 4)
                
                # Add some randomness to scrolling behavior
                if random.random() < 0.2:  # 20% chance to pause scrolling
                    logger.info("Taking a short break from scrolling")
                    self.human_behavior.random_sleep(2, 5)
            
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
                "div._aae- div"  # Another Instagram class
            ]
            
            for selector in item_selectors:
                try:
                    items = container.find_elements(By.CSS_SELECTOR, selector)
                    if items and len(items) > 0:
                        # Check if these items look like follower items (contain usernames or links)
                        for item in items[:5]:  # Check first few items
                            try:
                                # Check if item contains a link
                                links = item.find_elements(By.TAG_NAME, "a")
                                if links and len(links) > 0:
                                    follower_items = items
                                    logger.info(f"Found {len(follower_items)} follower items with selector: {selector}")
                                    break
                            except:
                                continue
                        
                        if follower_items:
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
        except Exception as e:
            logger.warning(f"Error getting follower items: {str(e)}")
        
        return follower_items
    
    def _process_follower_items(self, follower_items):
        """
        Process follower items and extract data.
        
        Args:
            follower_items: List of follower item elements
        """
        for item in follower_items:
            try:
                # Extract username with multiple approaches
                username = None
                fullname = ""
                profile_pic_url = ""
                is_verified = False
                
                # Approach 1: Extract from href attribute
                try:
                    links = item.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and "instagram.com/" in href and "/p/" not in href and "/explore/" not in href:
                            username = href.split("/")[-2] if href.endswith("/") else href.split("/")[-1]
                            break
                except:
                    pass
                
                # If we still don't have a username, try other approaches
                if not username:
                    try:
                        # Look for elements with a username
                        username_elements = item.find_elements(By.CSS_SELECTOR, "span, div")
                        for element in username_elements:
                            text = element.text
                            if text and text.startswith("@"):
                                username = text[1:]  # Remove the @ symbol
                                break
                            elif text and not text.isspace() and " " not in text and len(text) > 2:
                                # This might be a username
                                username = text
                                break
                    except:
                        pass
                
                # Skip if no username found
                if not username:
                    continue
                
                # Skip if already processed
                if username in [f["username"] for f in self.followers_data]:
                    continue
                
                # Extract full name
                try:
                    # Try different approaches to find the full name
                    name_elements = item.find_elements(By.CSS_SELECTOR, "span, div")
                    for element in name_elements:
                        text = element.text
                        if text and text != username and " " in text:
                            fullname = text
                            break
                except:
                    pass
                
                # Extract profile picture
                try:
                    img_elements = item.find_elements(By.TAG_NAME, "img")
                    for img in img_elements:
                        src = img.get_attribute("src")
                        if src and ("profile_pic" in src or "instagram" in src):
                            profile_pic_url = src
                            break
                except:
                    pass
                
                # Check if verified
                try:
                    verified_badges = item.find_elements(By.CSS_SELECTOR, "span[aria-label*='Verified']")
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
                logger.debug(f"Error processing follower item: {str(e)}")
                continue
    
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
                
                # Navigate to follower profile
                profile_url = PROFILE_URL.format(follower["username"])
                logger.info(f"Analyzing profile for {follower['username']}")
                
                self.navigate_to(profile_url)
                
                # Wait for the page to load
                self.human_behavior.random_sleep(3, 5)
                
                # Try to extract profile data from page source
                page_source = self.browser.page_source
                
                # Extract profile statistics
                profile_stats = self._extract_profile_statistics_ui()
                
                # Determine account type
                account_type = self._determine_account_type_ui()
                
                # Check if account is private
                is_private = self._is_account_private_ui()
                
                # Update follower data with detailed information
                follower.update({
                    "posts_count": profile_stats.get("posts", 0),
                    "followers_count": profile_stats.get("followers", 0),
                    "following_count": profile_stats.get("following", 0),
                    "account_type": account_type,
                    "is_private": is_private,
                    "detailed_profile_analyzed": True,
                    "profile_analyzed_at": datetime.now().isoformat()
                })
                
                analyzed_count += 1
                
                # Log progress
                if analyzed_count % 5 == 0:
                    logger.info(f"Analyzed {analyzed_count} profiles so far")
                    
                    # Save intermediate results
                    self.save_follower_data()
                
                # Add random delay between profile visits
                self.human_behavior.random_sleep(3, 5)
                
            except Exception as e:
                logger.warning(f"Error analyzing profile for {follower['username']}: {str(e)}")
                continue
        
        logger.info(f"Completed detailed analysis of {analyzed_count} follower profiles")
    
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
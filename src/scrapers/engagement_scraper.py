import time
import json
import os
import random
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from src.scrapers.scraper_base import ScraperBase
from src.utils.browser import wait_for_element, random_sleep, element_exists
from src.utils.logger import get_default_logger
from src.utils.error_handler import retry_on_exception, handle_selenium_exceptions, log_execution_time
from src.utils.human_behavior import HumanBehaviorSimulator

# Get logger
logger = get_default_logger()

# Instagram URLs
PROFILE_URL = "https://www.instagram.com/{}/"
POST_URL = "https://www.instagram.com/p/{}/"
STORY_URL = "https://www.instagram.com/stories/{}/"
REELS_URL = "https://www.instagram.com/reels/{}/"

# Selectors
LIKES_BUTTON = "section div span a[href*='liked_by']"
LIKES_DIALOG = "div[role='dialog']"
LIKES_LIST = "div[role='dialog'] div[style*='overflow-y'] div div"
LIKES_USERNAME = "a[href*='/']"
COMMENTS_SECTION = "ul[class*='comment'] li"
COMMENT_USERNAME = "a[href*='/']"
STORY_VIEWERS_BUTTON = "span[aria-label='View Story Viewers']"
STORY_VIEWERS_LIST = "div[role='dialog'] div[style*='overflow-y'] div div"
STORY_VIEWER_USERNAME = "a[href*='/']"
REEL_LIKES_BUTTON = "section div span a[href*='liked_by']"
REEL_COMMENTS_BUTTON = "section div span a[href*='comments']"
ACTIVE_NOW_INDICATOR = "span[aria-label='Active now']"

class EngagementScraper(ScraperBase):
    """
    Scraper for collecting engagement data from Instagram posts, stories, and reels.
    Extracts likes, comments, story views, and online activity data.
    """
    
    def __init__(self, target_username=None):
        """
        Initialize the engagement scraper.
        
        Args:
            target_username: The username whose engagement data to scrape. If None, uses the logged-in user.
        """
        super().__init__()
        self.target_username = target_username or self.username
        self.post_engagement_data = []
        self.story_engagement_data = []
        self.reel_engagement_data = []
        self.online_activity_data = []
        self._browser_passed_externally = False
        
    def run(self):
        """
        Main method to run the engagement scraper.
        
        Returns:
            Dictionary containing all engagement data
        """
        logger.info(f"Starting engagement data collection for {self.target_username}")
        
        try:
            # Start the browser if not already started
            if not self.browser:
                session_loaded = self.start()
                
                # Navigate to the target profile
                self.navigate_to(PROFILE_URL.format(self.target_username))
                
                # Add random delay
                self.human_behavior.random_sleep(2, 4)
            
            # Collect post engagement data
            try:
                logger.info("Starting post engagement collection")
                self.collect_post_engagement()
            except Exception as e:
                logger.error(f"Error during post engagement collection: {str(e)}")
                # Continue with other steps
            
            # Collect story engagement data
            try:
                logger.info("Starting story engagement collection")
                self.collect_story_engagement()
            except Exception as e:
                logger.error(f"Error during story engagement collection: {str(e)}")
                # Continue with other steps
            
            # Collect reel engagement data
            try:
                logger.info("Starting reel engagement collection")
                self.collect_reel_engagement()
            except Exception as e:
                logger.error(f"Error during reel engagement collection: {str(e)}")
                # Continue with other steps
            
            # Monitor online activity
            try:
                logger.info("Starting online activity monitoring")
                self.monitor_online_activity()
            except Exception as e:
                logger.error(f"Error during online activity monitoring: {str(e)}")
                # Continue with other steps
            
            # Save all collected data
            self.save_engagement_data()
            
            # Check if we collected any data
            total_data_points = (
                len(self.post_engagement_data) + 
                len(self.story_engagement_data) + 
                len(self.reel_engagement_data) + 
                len(self.online_activity_data)
            )
            
            if total_data_points == 0:
                logger.warning("No engagement data was collected")
            else:
                logger.info(f"Successfully collected {total_data_points} engagement data points")
            
            return {
                "post_engagement": self.post_engagement_data,
                "story_engagement": self.story_engagement_data,
                "reel_engagement": self.reel_engagement_data,
                "online_activity": self.online_activity_data
            }
            
        except Exception as e:
            logger.error(f"Error in engagement scraper: {str(e)}")
            # Return whatever data we've collected so far
            return {
                "post_engagement": self.post_engagement_data,
                "story_engagement": self.story_engagement_data,
                "reel_engagement": self.reel_engagement_data,
                "online_activity": self.online_activity_data
            }
        finally:
            # Save data before stopping
            try:
                self.save_engagement_data()
            except Exception as e:
                logger.error(f"Error saving engagement data: {str(e)}")
            
            # Only stop the browser if it wasn't passed externally
            if not self._browser_passed_externally and self.browser:
                self.stop()
    
    @retry_on_exception(max_retries=3)
    @handle_selenium_exceptions
    @log_execution_time
    def collect_post_engagement(self):
        """
        Collect engagement data from recent posts.
        Extracts likes and comments for each post.
        """
        logger.info(f"Collecting post engagement data for {self.target_username}")
        
        try:
            # Navigate to profile page
            self.navigate_to(PROFILE_URL.format(self.target_username))
            
            # Check for challenges
            if self._is_challenge_present():
                if not self._recover_session():
                    logger.error("Failed to recover from challenge")
                    return []
                
                # Try navigating to profile again
                self.navigate_to(PROFILE_URL.format(self.target_username))
            
            # Wait for posts to load
            wait_for_element(self.browser, "article a", timeout=10)
            
            # Get all post links
            post_links = self.browser.find_elements(By.CSS_SELECTOR, "article a")
            post_urls = [link.get_attribute("href") for link in post_links[:12]]  # Limit to recent 12 posts
            
            logger.info(f"Found {len(post_urls)} posts to analyze")
            
            for post_url in post_urls:
                try:
                    # Extract post ID from URL
                    post_id = post_url.split("/p/")[1].split("/")[0]
                    
                    # Navigate to post
                    self.navigate_to(post_url)
                    
                    # Check for challenges
                    if self._is_challenge_present():
                        if not self._recover_session():
                            logger.error("Failed to recover from challenge")
                            continue
                        
                        # Try navigating to post again
                        self.navigate_to(post_url)
                    
                    # Extract post data
                    post_data = {
                        "post_id": post_id,
                        "url": post_url,
                        "timestamp": datetime.now().isoformat(),
                        "likes": self._extract_post_likes(),
                        "comments": self._extract_post_comments(),
                        "view_count": self._extract_post_views()
                    }
                    
                    self.post_engagement_data.append(post_data)
                    logger.info(f"Collected engagement data for post {post_id}")
                    
                    # Save checkpoint after each post
                    self.save_engagement_data()
                    
                    # Add random delay between posts
                    self.human_behavior.random_sleep(3, 6)
                    
                except Exception as e:
                    logger.error(f"Error processing post {post_url}: {str(e)}")
            
            return self.post_engagement_data
            
        except Exception as e:
            logger.error(f"Error collecting post engagement: {str(e)}")
            raise
    
    def _extract_post_likes(self):
        """Extract likes from the current post."""
        try:
            # Click on likes count to open likes dialog
            likes_button = wait_for_element(self.browser, LIKES_BUTTON, timeout=5)
            likes_count_text = likes_button.text
            likes_count = int(''.join(filter(str.isdigit, likes_count_text)))
            
            # Only process if there are likes
            if likes_count > 0:
                # Click to open likes dialog
                self.human_behavior.click_element(likes_button)
                
                # Wait for dialog to appear
                wait_for_element(self.browser, LIKES_DIALOG, timeout=5)
                
                # Extract usernames from likes dialog
                like_elements = self.browser.find_elements(By.CSS_SELECTOR, LIKES_LIST)
                usernames = []
                
                for element in like_elements:
                    try:
                        username_element = element.find_element(By.CSS_SELECTOR, LIKES_USERNAME)
                        username = username_element.get_attribute("href").split("/")[-2]
                        usernames.append(username)
                    except:
                        continue
                
                # Close dialog by pressing Escape
                ActionChains(self.browser).send_keys(Keys.ESCAPE).perform()
                
                return {
                    "count": likes_count,
                    "usernames": usernames
                }
            else:
                return {
                    "count": 0,
                    "usernames": []
                }
                
        except Exception as e:
            logger.error(f"Error extracting post likes: {str(e)}")
            return {
                "count": 0,
                "usernames": []
            }
    
    def _extract_post_comments(self):
        """Extract comments from the current post."""
        try:
            # Find comment section
            comment_elements = self.browser.find_elements(By.CSS_SELECTOR, COMMENTS_SECTION)
            
            comments = []
            for element in comment_elements:
                try:
                    username_element = element.find_element(By.CSS_SELECTOR, COMMENT_USERNAME)
                    username = username_element.get_attribute("href").split("/")[-2]
                    
                    # Get comment text
                    comment_text = element.text.split("\n")[1] if "\n" in element.text else ""
                    
                    comments.append({
                        "username": username,
                        "text": comment_text
                    })
                except:
                    continue
            
            return {
                "count": len(comments),
                "comments": comments
            }
                
        except Exception as e:
            logger.error(f"Error extracting post comments: {str(e)}")
            return {
                "count": 0,
                "comments": []
            }
    
    def _extract_post_views(self):
        """Extract view count if available (for videos)."""
        try:
            # Check if view count element exists
            view_count_element = self.browser.find_element(By.CSS_SELECTOR, "span[class*='view'] span")
            view_count_text = view_count_element.text
            view_count = int(''.join(filter(str.isdigit, view_count_text)))
            return view_count
        except:
            return None
    
    @retry_on_exception(max_retries=3)
    @handle_selenium_exceptions
    @log_execution_time
    def collect_story_engagement(self):
        """
        Collect engagement data from recent stories.
        Extracts story viewers and their usernames.
        """
        logger.info(f"Collecting story engagement data for {self.target_username}")
        
        try:
            # Navigate to stories page
            self.navigate_to(STORY_URL.format(self.target_username))
            
            # Check for challenges
            if self._is_challenge_present():
                if not self._recover_session():
                    logger.error("Failed to recover from challenge")
                    return []
                
                # Try navigating to stories again
                self.navigate_to(STORY_URL.format(self.target_username))
            
            # Check if stories exist
            if "No stories to show" in self.browser.page_source:
                logger.info(f"No active stories found for {self.target_username}")
                return []
            
            # Wait for story to load with a shorter timeout
            try:
                wait_for_element(self.browser, "section", timeout=5)
            except TimeoutException:
                logger.info("No story section found, user may not have active stories")
                return []
            
            # Check if viewers button exists
            if not element_exists(self.browser, STORY_VIEWERS_BUTTON):
                logger.info("No story viewers button found, user may not have active stories or you can't see viewers")
                return []
            
            # Click on viewers button if available
            try:
                viewers_button = wait_for_element(self.browser, STORY_VIEWERS_BUTTON, timeout=5)
                if not viewers_button:
                    logger.info("No viewers button found, user may not have active stories or you can't see viewers")
                    return []
                    
                self.human_behavior.click_element(viewers_button)
                
                # Wait for viewers dialog
                viewers_dialog = wait_for_element(self.browser, STORY_VIEWERS_LIST, timeout=5)
                if not viewers_dialog:
                    logger.info("No viewers dialog found after clicking viewers button")
                    return []
                
                # Extract viewer usernames
                viewer_elements = self.browser.find_elements(By.CSS_SELECTOR, STORY_VIEWERS_LIST)
                viewers = []
                
                for element in viewer_elements:
                    try:
                        username_element = element.find_element(By.CSS_SELECTOR, STORY_VIEWER_USERNAME)
                        username = username_element.get_attribute("href").split("/")[-2]
                        viewers.append(username)
                    except:
                        continue
                
                # Store story data
                story_data = {
                    "timestamp": datetime.now().isoformat(),
                    "viewer_count": len(viewers),
                    "viewers": viewers
                }
                
                self.story_engagement_data.append(story_data)
                logger.info(f"Collected {len(viewers)} story viewers")
                
                # Save checkpoint
                self.save_engagement_data()
                
                # Close dialog by pressing Escape
                ActionChains(self.browser).send_keys(Keys.ESCAPE).perform()
                
            except TimeoutException:
                logger.info("No viewers button found or no viewers for this story")
            except Exception as e:
                logger.error(f"Error extracting story viewers: {str(e)}")
            
            return self.story_engagement_data
            
        except Exception as e:
            logger.error(f"Error collecting story engagement: {str(e)}")
            return []
    
    @retry_on_exception(max_retries=3)
    @handle_selenium_exceptions
    @log_execution_time
    def collect_reel_engagement(self):
        """
        Collect engagement data from recent reels.
        Extracts likes, comments, and view counts.
        """
        logger.info(f"Collecting reel engagement data for {self.target_username}")
        
        try:
            # Navigate to profile page
            self.navigate_to(PROFILE_URL.format(self.target_username))
            
            # Check for challenges
            if self._is_challenge_present():
                if not self._recover_session():
                    logger.error("Failed to recover from challenge")
                    return []
                
                # Try navigating to profile again
                self.navigate_to(PROFILE_URL.format(self.target_username))
            
            # Click on Reels tab
            tabs = self.browser.find_elements(By.CSS_SELECTOR, "a[href*='reels']")
            if tabs:
                self.human_behavior.click_element(tabs[0])
                
                # Wait for reels to load
                wait_for_element(self.browser, "article a", timeout=10)
                
                # Get all reel links
                reel_links = self.browser.find_elements(By.CSS_SELECTOR, "article a")
                reel_urls = [link.get_attribute("href") for link in reel_links[:10]]  # Limit to recent 10 reels
                
                logger.info(f"Found {len(reel_urls)} reels to analyze")
                
                for reel_url in reel_urls:
                    try:
                        # Extract reel ID from URL
                        reel_id = reel_url.split("/reel/")[1].split("/")[0]
                        
                        # Navigate to reel
                        self.navigate_to(reel_url)
                        
                        # Check for challenges
                        if self._is_challenge_present():
                            if not self._recover_session():
                                logger.error("Failed to recover from challenge")
                                continue
                            
                            # Try navigating to reel again
                            self.navigate_to(reel_url)
                        
                        # Extract reel data
                        reel_data = {
                            "reel_id": reel_id,
                            "url": reel_url,
                            "timestamp": datetime.now().isoformat(),
                            "likes": self._extract_reel_likes(),
                            "comments": self._extract_reel_comments(),
                            "view_count": self._extract_reel_views()
                        }
                        
                        self.reel_engagement_data.append(reel_data)
                        logger.info(f"Collected engagement data for reel {reel_id}")
                        
                        # Save checkpoint after each reel
                        self.save_engagement_data()
                        
                        # Add random delay between reels
                        self.human_behavior.random_sleep(3, 6)
                        
                    except Exception as e:
                        logger.error(f"Error processing reel {reel_url}: {str(e)}")
            else:
                logger.info(f"No reels tab found for {self.target_username}")
            
            return self.reel_engagement_data
            
        except Exception as e:
            logger.error(f"Error collecting reel engagement: {str(e)}")
            raise
    
    def _extract_reel_likes(self):
        """Extract likes from the current reel."""
        try:
            # Similar to post likes extraction
            likes_button = wait_for_element(self.browser, REEL_LIKES_BUTTON, timeout=5)
            likes_count_text = likes_button.text
            likes_count = int(''.join(filter(str.isdigit, likes_count_text)))
            
            # Only process if there are likes
            if likes_count > 0:
                # Click to open likes dialog
                self.human_behavior.click_element(likes_button)
                
                # Wait for dialog to appear
                wait_for_element(self.browser, LIKES_DIALOG, timeout=5)
                
                # Extract usernames from likes dialog
                like_elements = self.browser.find_elements(By.CSS_SELECTOR, LIKES_LIST)
                usernames = []
                
                for element in like_elements:
                    try:
                        username_element = element.find_element(By.CSS_SELECTOR, LIKES_USERNAME)
                        username = username_element.get_attribute("href").split("/")[-2]
                        usernames.append(username)
                    except:
                        continue
                
                # Close dialog by pressing Escape
                ActionChains(self.browser).send_keys(Keys.ESCAPE).perform()
                
                return {
                    "count": likes_count,
                    "usernames": usernames
                }
            else:
                return {
                    "count": 0,
                    "usernames": []
                }
                
        except Exception as e:
            logger.error(f"Error extracting reel likes: {str(e)}")
            return {
                "count": 0,
                "usernames": []
            }
    
    def _extract_reel_comments(self):
        """Extract comments from the current reel."""
        try:
            # Similar to post comments extraction
            comment_elements = self.browser.find_elements(By.CSS_SELECTOR, COMMENTS_SECTION)
            
            comments = []
            for element in comment_elements:
                try:
                    username_element = element.find_element(By.CSS_SELECTOR, COMMENT_USERNAME)
                    username = username_element.get_attribute("href").split("/")[-2]
                    
                    # Get comment text
                    comment_text = element.text.split("\n")[1] if "\n" in element.text else ""
                    
                    comments.append({
                        "username": username,
                        "text": comment_text
                    })
                except:
                    continue
            
            return {
                "count": len(comments),
                "comments": comments
            }
                
        except Exception as e:
            logger.error(f"Error extracting reel comments: {str(e)}")
            return {
                "count": 0,
                "comments": []
            }
    
    def _extract_reel_views(self):
        """Extract view count from the current reel."""
        try:
            # Check if view count element exists
            view_count_element = self.browser.find_element(By.CSS_SELECTOR, "span[class*='view'] span")
            view_count_text = view_count_element.text
            view_count = int(''.join(filter(str.isdigit, view_count_text)))
            return view_count
        except:
            return None
    
    @retry_on_exception(max_retries=3)
    @handle_selenium_exceptions
    @log_execution_time
    def monitor_online_activity(self):
        """
        Monitor online activity of followers.
        Detects 'Active Now' status and tracks timing patterns.
        """
        logger.info(f"Monitoring online activity for followers of {self.target_username}")
        
        try:
            # First try to find follower data in the data/followers directory
            followers_data = self._load_follower_data_from_files()
            
            if not followers_data:
                # If no data found in data/followers, try the regular data directory
                followers_file = os.path.join("data", f"{self.target_username}_followers.json")
                
                if not os.path.exists(followers_file):
                    logger.warning(f"No followers data found for {self.target_username}")
                    return []
                
                with open(followers_file, 'r') as f:
                    followers_data = json.load(f)
            
            # Sample a subset of followers to check (to avoid rate limiting)
            sample_size = min(50, len(followers_data))
            sampled_followers = random.sample(followers_data, sample_size)
            
            logger.info(f"Checking online status for {sample_size} followers")
            
            for i, follower in enumerate(sampled_followers):
                try:
                    username = follower.get('username')
                    if not username:
                        continue
                    
                    # Navigate to follower's profile
                    self.navigate_to(PROFILE_URL.format(username))
                    
                    # Check for challenges
                    if self._is_challenge_present():
                        if not self._recover_session():
                            logger.error("Failed to recover from challenge")
                            continue
                        
                        # Try navigating to profile again
                        self.navigate_to(PROFILE_URL.format(username))
                    
                    # Check for "Active Now" indicator
                    is_active = element_exists(self.browser, ACTIVE_NOW_INDICATOR)
                    
                    activity_data = {
                        "username": username,
                        "timestamp": datetime.now().isoformat(),
                        "is_active": is_active
                    }
                    
                    self.online_activity_data.append(activity_data)
                    
                    # Save checkpoint every 10 profiles
                    if i % 10 == 0:
                        self.save_engagement_data()
                    
                    # Add random delay between profile checks
                    self.human_behavior.random_sleep(2, 5)
                    
                except Exception as e:
                    logger.error(f"Error checking activity for {username}: {str(e)}")
            
            # Final save
            self.save_engagement_data()
            
            return self.online_activity_data
            
        except Exception as e:
            logger.error(f"Error monitoring online activity: {str(e)}")
            return []
            
    def _load_follower_data_from_files(self):
        """
        Load follower data from files in the data/followers directory.
        Returns the most recent follower data file for the target username.
        
        Returns:
            List of follower data dictionaries or None if no data found
        """
        try:
            # Check if data/followers directory exists
            followers_dir = os.path.join("data", "followers")
            if not os.path.exists(followers_dir):
                logger.warning(f"Followers directory not found: {followers_dir}")
                return None
            
            # Get all JSON files for the target username
            follower_files = []
            for filename in os.listdir(followers_dir):
                if filename.startswith(f"{self.target_username}_followers_") and filename.endswith(".json"):
                    file_path = os.path.join(followers_dir, filename)
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)
                    follower_files.append((file_path, mod_time))
            
            if not follower_files:
                logger.warning(f"No follower data files found for {self.target_username}")
                return None
            
            # Sort by modification time (newest first)
            follower_files.sort(key=lambda x: x[1], reverse=True)
            
            # Load the most recent file
            most_recent_file = follower_files[0][0]
            logger.info(f"Loading follower data from {most_recent_file}")
            
            with open(most_recent_file, 'r') as f:
                data = json.load(f)
            
            # Check if the data is a dictionary with a 'followers' key
            if isinstance(data, dict) and 'followers' in data:
                return data['followers']
            
            # Otherwise, assume it's a list of followers
            return data
            
        except Exception as e:
            logger.error(f"Error loading follower data from files: {str(e)}")
            return None
    
    def save_engagement_data(self):
        """Save all collected engagement data to JSON files."""
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        
        # Save post engagement data
        if self.post_engagement_data:
            post_file = os.path.join(data_dir, f"{self.target_username}_post_engagement.json")
            with open(post_file, 'w') as f:
                json.dump(self.post_engagement_data, f, indent=4)
            logger.info(f"Post engagement data saved to {post_file}")
        
        # Save story engagement data
        if self.story_engagement_data:
            story_file = os.path.join(data_dir, f"{self.target_username}_story_engagement.json")
            with open(story_file, 'w') as f:
                json.dump(self.story_engagement_data, f, indent=4)
            logger.info(f"Story engagement data saved to {story_file}")
        
        # Save reel engagement data
        if self.reel_engagement_data:
            reel_file = os.path.join(data_dir, f"{self.target_username}_reel_engagement.json")
            with open(reel_file, 'w') as f:
                json.dump(self.reel_engagement_data, f, indent=4)
            logger.info(f"Reel engagement data saved to {reel_file}")
        
        # Save online activity data
        if self.online_activity_data:
            activity_file = os.path.join(data_dir, f"{self.target_username}_online_activity.json")
            with open(activity_file, 'w') as f:
                json.dump(self.online_activity_data, f, indent=4)
            logger.info(f"Online activity data saved to {activity_file}")
            
    def _recover_session(self):
        """
        Attempt to recover from a failed session.
        This method tries to restart the browser and log in again.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        logger.info("Attempting to recover session")
        
        try:
            # First try to handle login challenges without restarting
            if self._handle_login_challenge():
                logger.info("Successfully handled login challenge")
                return True
            
            # If handling the challenge didn't work, try restarting the browser
            logger.info("Restarting browser for session recovery")
            
            # Close the current browser
            if self.browser:
                self.browser.quit()
                self.browser = None
            
            # Start a new browser
            session_loaded = self.start()
            
            # Check if we need to navigate to the target profile
            if session_loaded and self.target_username:
                self.navigate_to(PROFILE_URL.format(self.target_username))
                self.human_behavior.random_sleep(2, 4)
                
                # Check for challenges again
                if self._is_challenge_present():
                    if not self._handle_login_challenge():
                        logger.error("Failed to handle login challenge after restart")
                        return False
            
            logger.info("Session recovery successful")
            return True
            
        except Exception as e:
            logger.error(f"Session recovery failed: {str(e)}")
            return False
            
    def _is_challenge_present(self):
        """
        Check if Instagram is showing a challenge or verification screen.
        
        Returns:
            True if a challenge is detected, False otherwise
        """
        challenge_indicators = [
            "suspicious login attempt",
            "confirm your identity",
            "verify it's you",
            "enter security code",
            "we detected an unusual login",
            "enter the confirmation code",
            "challenge_required",
            "this was me",
            "save login info",
            "save your login info",
            "turn on notifications",
            "add your birthday",
            "confirm your age",
            "we need to confirm your age",
            "we need more information",
            "your account has been temporarily locked",
            "we've detected unusual activity",
            "we limit how often",
            "try again later",
            "couldn't refresh feed",
            "please wait a few minutes before you try again",
            "feedback_required"
        ]
        
        try:
            page_source = self.browser.page_source.lower()
            
            for indicator in challenge_indicators:
                if indicator in page_source:
                    logger.warning(f"Challenge detected: '{indicator}'")
                    return True
            
            # Also check for specific elements that indicate challenges
            challenge_elements = [
                "//button[contains(text(), 'This Was Me')]",
                "//button[contains(text(), 'Save Info')]",
                "//button[contains(text(), 'Not Now')]",
                "//button[contains(text(), 'Try Again')]",
                "//button[contains(text(), 'OK')]",
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'Send Security Code')]",
                "input[name='verificationCode']",
                "input[aria-label='Security code']"
            ]
            
            for element_selector in challenge_elements:
                if element_selector.startswith("//"):
                    if element_exists(self.browser, element_selector, by=By.XPATH):
                        logger.warning(f"Challenge element detected: '{element_selector}'")
                        return True
                else:
                    if element_exists(self.browser, element_selector):
                        logger.warning(f"Challenge element detected: '{element_selector}'")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for challenges: {str(e)}")
            return False
    
    def _handle_login_challenge(self):
        """
        Handle login challenges that might appear during scraping.
        This method attempts to handle suspicious login attempts and other challenges.
        
        Returns:
            True if challenge was handled successfully, False otherwise
        """
        logger.info("Attempting to handle login challenge")
        
        try:
            page_source = self.browser.page_source.lower()
            
            # Check for suspicious login button
            if "suspicious login attempt" in page_source or "this was me" in page_source:
                suspicious_button = wait_for_element(self.browser, "//button[contains(text(), 'This Was Me')]", by=By.XPATH, timeout=5)
                
                if suspicious_button:
                    logger.info("Found 'This Was Me' button, clicking it")
                    self.human_behavior.click_element(suspicious_button)
                    self.human_behavior.random_sleep(3, 5)
                    return True
            
            # Check for "Save Login Info" prompt
            if "save login info" in page_source or "save your login info" in page_source:
                save_button = wait_for_element(self.browser, "//button[contains(text(), 'Save Info') or contains(text(), 'Not Now')]", by=By.XPATH, timeout=5)
                
                if save_button:
                    logger.info("Found 'Save Login Info' prompt, clicking 'Not Now'")
                    self.human_behavior.click_element(save_button)
                    self.human_behavior.random_sleep(2, 4)
                    return True
            
            # Check for notifications prompt
            if "turn on notifications" in page_source:
                notifications_button = wait_for_element(self.browser, "//button[contains(text(), 'Not Now')]", by=By.XPATH, timeout=5)
                
                if notifications_button:
                    logger.info("Found notifications prompt, clicking 'Not Now'")
                    self.human_behavior.click_element(notifications_button)
                    self.human_behavior.random_sleep(2, 4)
                    return True
            
            # If we reach here, we couldn't handle the challenge
            logger.warning("Could not identify or handle the login challenge")
            return False
            
        except Exception as e:
            logger.error(f"Error handling login challenge: {str(e)}")
            return False
    
    def set_browser(self, browser):
        """
        Set the browser and initialize human behavior simulator.
        
        Args:
            browser: Selenium WebDriver instance
        """
        self.browser = browser
        self.human_behavior = HumanBehaviorSimulator(browser)
        self._browser_passed_externally = True 
        
    def simulate_engagement_data(self):
        """
        Simulate engagement data for testing purposes.
        This method generates fake engagement data based on follower data.
        
        Returns:
            Dictionary containing simulated engagement data
        """
        logger.info(f"Simulating engagement data for {self.target_username}")
        
        try:
            # Load follower data
            followers_data = self._load_follower_data_from_files()
            
            if not followers_data:
                logger.warning("No follower data found, cannot simulate engagement")
                return False
            
            # Get a list of usernames
            usernames = [follower.get('username') for follower in followers_data if follower.get('username')]
            
            if not usernames:
                logger.warning("No usernames found in follower data")
                return False
            
            # Simulate post engagement
            for i in range(5):  # Simulate 5 posts
                post_id = f"simulated_post_{i}"
                post_url = f"https://www.instagram.com/p/{post_id}/"
                
                # Randomly select some followers who liked the post
                like_count = random.randint(10, min(50, len(usernames)))
                likers = random.sample(usernames, like_count)
                
                # Randomly select some followers who commented on the post
                comment_count = random.randint(0, min(10, len(usernames)))
                commenters = random.sample(usernames, comment_count)
                
                comments = []
                for commenter in commenters:
                    comments.append({
                        "username": commenter,
                        "text": f"Simulated comment by {commenter}"
                    })
                
                post_data = {
                    "post_id": post_id,
                    "url": post_url,
                    "timestamp": datetime.now().isoformat(),
                    "likes": {
                        "count": like_count,
                        "usernames": likers
                    },
                    "comments": {
                        "count": comment_count,
                        "comments": comments
                    },
                    "view_count": random.randint(100, 500) if random.random() > 0.5 else None
                }
                
                self.post_engagement_data.append(post_data)
            
            # Simulate story engagement
            story_data = {
                "timestamp": datetime.now().isoformat(),
                "viewer_count": random.randint(20, min(100, len(usernames))),
                "viewers": random.sample(usernames, random.randint(20, min(100, len(usernames))))
            }
            
            self.story_engagement_data.append(story_data)
            
            # Simulate reel engagement
            for i in range(3):  # Simulate 3 reels
                reel_id = f"simulated_reel_{i}"
                reel_url = f"https://www.instagram.com/reel/{reel_id}/"
                
                # Randomly select some followers who liked the reel
                like_count = random.randint(15, min(70, len(usernames)))
                likers = random.sample(usernames, like_count)
                
                # Randomly select some followers who commented on the reel
                comment_count = random.randint(0, min(15, len(usernames)))
                commenters = random.sample(usernames, comment_count)
                
                comments = []
                for commenter in commenters:
                    comments.append({
                        "username": commenter,
                        "text": f"Simulated reel comment by {commenter}"
                    })
                
                reel_data = {
                    "reel_id": reel_id,
                    "url": reel_url,
                    "timestamp": datetime.now().isoformat(),
                    "likes": {
                        "count": like_count,
                        "usernames": likers
                    },
                    "comments": {
                        "count": comment_count,
                        "comments": comments
                    },
                    "view_count": random.randint(200, 1000)
                }
                
                self.reel_engagement_data.append(reel_data)
            
            # Simulate online activity
            sample_size = min(50, len(usernames))
            sampled_usernames = random.sample(usernames, sample_size)
            
            for username in sampled_usernames:
                activity_data = {
                    "username": username,
                    "timestamp": datetime.now().isoformat(),
                    "is_active": random.random() > 0.8  # 20% chance of being active
                }
                
                self.online_activity_data.append(activity_data)
            
            # Save the simulated data
            self.save_engagement_data()
            
            logger.info(f"Successfully simulated engagement data: {len(self.post_engagement_data)} posts, "
                       f"{len(self.story_engagement_data)} stories, {len(self.reel_engagement_data)} reels, "
                       f"{len(self.online_activity_data)} activity records")
            
            return True
            
        except Exception as e:
            logger.error(f"Error simulating engagement data: {str(e)}")
            return False 
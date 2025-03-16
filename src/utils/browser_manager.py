import os
import random
import json
import time
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException

from src.utils.browser import setup_browser, random_sleep
from src.utils.logger import get_default_logger
from src.config.config import (
    MAX_RETRIES,
    DELAY_BETWEEN_REQUESTS_MIN,
    DELAY_BETWEEN_REQUESTS_MAX
)

# Get logger
logger = get_default_logger()

class BrowserManager:
    """
    Manages browser instances with advanced features like:
    - User-agent rotation
    - Cookie management
    - Session persistence
    - Automatic retries
    - Anti-detection measures
    """
    
    def __init__(self):
        self.browser = None
        self.session_start_time = None
        self.request_count = 0
        self.last_request_time = None
        self.user_agents = self._load_user_agents()
        
    def _load_user_agents(self):
        """Load user agents from file or use defaults."""
        user_agents_file = os.path.join('src', 'config', 'user_agents.txt')
        default_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        
        try:
            if os.path.exists(user_agents_file):
                with open(user_agents_file, 'r') as f:
                    agents = [line.strip() for line in f if line.strip()]
                if agents:
                    return agents
        except Exception as e:
            logger.warning(f"Error loading user agents: {e}")
        
        return default_agents
    
    def start_browser(self):
        """Start a new browser instance with a random user agent."""
        if self.browser:
            self.close_browser()
        
        # Rotate user agent
        user_agent = random.choice(self.user_agents)
        os.environ['USER_AGENT'] = user_agent
        
        self.browser = setup_browser()
        self.session_start_time = datetime.now()
        self.request_count = 0
        self.last_request_time = None
        
        logger.info(f"Started new browser session with user agent: {user_agent}")
        return self.browser
    
    def close_browser(self):
        """Safely close the browser."""
        if self.browser:
            try:
                self.browser.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.browser = None
    
    def restart_browser(self):
        """Restart the browser with a new user agent."""
        logger.info("Restarting browser...")
        self.close_browser()
        return self.start_browser()
    
    def execute_with_retry(self, func, *args, max_retries=None, **kwargs):
        """
        Execute a function with automatic retries on failure.
        
        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            max_retries: Maximum number of retries (default: from config)
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        if max_retries is None:
            max_retries = MAX_RETRIES
            
        retries = 0
        last_exception = None
        
        while retries <= max_retries:
            try:
                # Add delay between requests
                self._throttle_request()
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Update request count
                self.request_count += 1
                self.last_request_time = datetime.now()
                
                return result
            
            except WebDriverException as e:
                last_exception = e
                retries += 1
                
                logger.warning(f"Request failed (attempt {retries}/{max_retries}): {str(e)}")
                
                if "detected" in str(e).lower() or "automation" in str(e).lower():
                    logger.warning("Possible detection, restarting browser...")
                    self.restart_browser()
                
                # Exponential backoff
                wait_time = 2 ** retries + random.uniform(0, 1)
                logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
                time.sleep(wait_time)
        
        logger.error(f"Failed after {max_retries} retries: {last_exception}")
        raise last_exception
    
    def _throttle_request(self):
        """Add random delay between requests to avoid detection."""
        if self.last_request_time:
            # Calculate time since last request
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            
            # Determine delay based on request count (more requests = longer delays)
            min_delay = DELAY_BETWEEN_REQUESTS_MIN
            max_delay = DELAY_BETWEEN_REQUESTS_MAX
            
            # Adjust delay based on request count
            if self.request_count > 50:
                min_delay *= 1.5
                max_delay *= 1.5
            elif self.request_count > 100:
                min_delay *= 2
                max_delay *= 2
            
            # Calculate required delay
            required_delay = random.uniform(min_delay, max_delay)
            
            # Sleep if needed
            if elapsed < required_delay:
                sleep_time = required_delay - elapsed
                logger.debug(f"Throttling request, sleeping for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
    
    def simulate_human_behavior(self):
        """Simulate human-like behavior to avoid detection."""
        if not self.browser:
            return
        
        try:
            # Random scrolling
            scroll_amount = random.randint(100, 800)
            self.browser.execute_script(f"window.scrollBy(0, {scroll_amount});")
            random_sleep(0.5, 2)
            
            # Random mouse movements
            actions = ActionChains(self.browser)
            for _ in range(random.randint(1, 5)):
                x = random.randint(0, 500)
                y = random.randint(0, 500)
                actions.move_by_offset(x, y)
                actions.perform()
                random_sleep(0.1, 0.5)
            
            # Reset mouse position
            actions.move_to_element(self.browser.find_element_by_tag_name('body'))
            actions.perform()
            
        except Exception as e:
            logger.debug(f"Error during human behavior simulation: {e}")
    
    def save_session_state(self, username):
        """Save the current session state for future recovery."""
        if not self.browser:
            return
        
        try:
            session_dir = os.path.join("data", "sessions")
            os.makedirs(session_dir, exist_ok=True)
            
            session_file = os.path.join(session_dir, f"{username}_session.json")
            
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "request_count": self.request_count,
                "cookies": self.browser.get_cookies()
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
                
            logger.info(f"Session state saved to {session_file}")
            
        except Exception as e:
            logger.error(f"Error saving session state: {e}")
    
    def load_session_state(self, username):
        """Load a previously saved session state."""
        session_file = os.path.join("data", "sessions", f"{username}_session.json")
        
        if not os.path.exists(session_file):
            logger.info(f"No session file found for {username}")
            return False
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Start a new browser if needed
            if not self.browser:
                self.start_browser()
            
            # Load cookies
            for cookie in session_data.get("cookies", []):
                try:
                    self.browser.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Error adding cookie: {e}")
            
            # Update session info
            self.request_count = session_data.get("request_count", 0)
            self.last_request_time = datetime.now()
            
            logger.info(f"Session state loaded from {session_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading session state: {e}")
            return False 
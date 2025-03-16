import time
from abc import ABC, abstractmethod

from src.utils.browser_manager import BrowserManager
from src.utils.proxy_manager import ProxyManager
from src.utils.human_behavior import HumanBehaviorSimulator
from src.utils.error_handler import (
    retry_on_exception, 
    handle_selenium_exceptions,
    log_execution_time,
    ScraperException
)
from src.utils.logger import get_default_logger
from src.config.config import INSTAGRAM_USERNAME

# Get logger
logger = get_default_logger()

class ScraperBase(ABC):
    """
    Base class for all scrapers with common functionality.
    Implements browser management, proxy rotation, error handling,
    and anti-detection measures.
    """
    
    def __init__(self):
        """Initialize the scraper with browser and proxy managers."""
        self.browser_manager = BrowserManager()
        self.proxy_manager = ProxyManager()
        self.browser = None
        self.human_behavior = None
        self.username = INSTAGRAM_USERNAME
    
    def start(self):
        """Start the scraper by initializing the browser."""
        logger.info("Starting scraper...")
        
        # Get a proxy if enabled
        proxy = self.proxy_manager.get_proxy()
        if proxy:
            logger.info(f"Using proxy: {proxy}")
        
        # Start the browser
        self.browser = self.browser_manager.start_browser()
        
        # Initialize human behavior simulator
        self.human_behavior = HumanBehaviorSimulator(self.browser)
        
        # Try to load saved session
        session_loaded = self.browser_manager.load_session_state(self.username)
        
        logger.info(f"Scraper started successfully. Session loaded: {session_loaded}")
        return session_loaded
    
    def stop(self):
        """Stop the scraper and clean up resources."""
        logger.info("Stopping scraper...")
        
        # Save session state
        if self.browser:
            self.browser_manager.save_session_state(self.username)
        
        # Save proxy performance data
        self.proxy_manager.save_proxy_performance()
        
        # Close the browser
        self.browser_manager.close_browser()
        
        logger.info("Scraper stopped successfully")
    
    @abstractmethod
    def run(self):
        """
        Main method to run the scraper. Must be implemented by subclasses.
        
        Returns:
            The scraped data
        """
        pass
    
    @retry_on_exception(max_retries=3)
    @handle_selenium_exceptions
    @log_execution_time
    def navigate_to(self, url):
        """
        Navigate to a URL with error handling and retry logic.
        
        Args:
            url: The URL to navigate to
        """
        logger.info(f"Navigating to {url}")
        
        try:
            self.browser.get(url)
            
            # Add random delay after navigation
            self.human_behavior.random_sleep(2, 4)
            
            # Simulate human behavior
            self.human_behavior.random_activity(duration=2)
            
            # Mark proxy as successful
            self.proxy_manager.mark_proxy_success()
            
            return True
            
        except Exception as e:
            # Check if this might be an IP ban
            if "unusual traffic" in self.browser.page_source.lower() or "suspicious" in self.browser.page_source.lower():
                logger.warning("Possible IP ban detected")
                self.proxy_manager.mark_proxy_failure(ban=True)
                
                # Restart browser with new proxy
                self.browser = self.browser_manager.restart_browser()
                self.human_behavior = HumanBehaviorSimulator(self.browser)
            else:
                self.proxy_manager.mark_proxy_failure()
                
            raise ScraperException(f"Navigation failed: {str(e)}")
    
    def wait_and_refresh(self, seconds=60):
        """
        Wait for a specified time and then refresh the page.
        Useful for rate limiting situations.
        
        Args:
            seconds: Time to wait in seconds
        """
        logger.info(f"Waiting for {seconds} seconds before refreshing...")
        
        # Wait with a countdown
        for remaining in range(seconds, 0, -5):
            logger.debug(f"Refreshing in {remaining} seconds...")
            time.sleep(5)
        
        # Refresh the page
        self.browser.refresh()
        
        # Add random delay after refresh
        self.human_behavior.random_sleep(2, 4)
    
    def extract_data_safely(self, extractor_func, *args, **kwargs):
        """
        Safely extract data with error handling.
        
        Args:
            extractor_func: Function to extract data
            *args, **kwargs: Arguments to pass to the extractor function
            
        Returns:
            The extracted data or None on failure
        """
        try:
            return extractor_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Data extraction failed: {str(e)}")
            return None 
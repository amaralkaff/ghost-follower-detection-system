import random
import time
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config.config import (
    HEADLESS_MODE,
    USER_AGENT,
    USE_PROXY,
    PROXY_LIST_PATH,
    REQUEST_TIMEOUT
)

def get_random_proxy():
    """Get a random proxy from the proxy list file."""
    if not USE_PROXY:
        return None
    
    try:
        with open(PROXY_LIST_PATH, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        
        if not proxies:
            print("Warning: Proxy list is empty. Proceeding without proxy.")
            return None
        
        return random.choice(proxies)
    except FileNotFoundError:
        print(f"Warning: Proxy list file {PROXY_LIST_PATH} not found. Proceeding without proxy.")
        return None

def setup_browser():
    """Set up and return an undetected Chrome browser instance."""
    # Create Chrome options
    options = uc.ChromeOptions()
    
    # Set user agent
    options.add_argument(f'user-agent={USER_AGENT}')
    
    # Add proxy if enabled
    proxy = get_random_proxy()
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    
    # Add additional options to make browser more stealthy
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-browser-side-navigation')
    options.add_argument('--disable-gpu')
    
    # Handle headless mode
    if HEADLESS_MODE:
        options.add_argument('--headless')
    
    try:
        # Create and return the browser instance with headless parameter
        browser = uc.Chrome(
            options=options,
            use_subprocess=True
        )
        browser.set_page_load_timeout(REQUEST_TIMEOUT)
        return browser
    except Exception as e:
        print(f"Error creating Chrome instance with options: {str(e)}")
        # Fallback to a simpler configuration
        try:
            browser = uc.Chrome(use_subprocess=True)
            browser.set_page_load_timeout(REQUEST_TIMEOUT)
            return browser
        except Exception as e:
            print(f"Error creating Chrome instance with fallback: {str(e)}")
            raise

def random_sleep(min_seconds=1, max_seconds=3):
    """Sleep for a random amount of time between min and max seconds."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def scroll_to_bottom(browser, scroll_pause_time=1.0, num_scrolls=None):
    """
    Scroll to the bottom of a page.
    
    Args:
        browser: The browser instance
        scroll_pause_time: Time to pause between scrolls
        num_scrolls: Maximum number of scrolls (None for unlimited)
    """
    # Get scroll height
    last_height = browser.execute_script("return document.body.scrollHeight")
    
    scrolls = 0
    while num_scrolls is None or scrolls < num_scrolls:
        # Scroll down
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Add some randomness to the scrolling
        random_sleep(0.5, 1.5)
        
        # Calculate new scroll height and compare with last scroll height
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scrolls += 1

def wait_for_element(browser, selector, by=By.CSS_SELECTOR, timeout=10):
    """
    Wait for an element to be present on the page.
    
    Args:
        browser: The browser instance
        selector: The CSS selector or XPath
        by: The selector type (By.CSS_SELECTOR, By.XPATH, etc.)
        timeout: Maximum time to wait in seconds
        
    Returns:
        The element if found, None otherwise
    """
    try:
        element = WebDriverWait(browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        print(f"Timeout waiting for element: {selector}")
        return None

def element_exists(browser, selector, by=By.CSS_SELECTOR):
    """
    Check if an element exists on the page.
    
    Args:
        browser: The browser instance
        selector: The CSS selector or XPath
        by: The selector type (By.CSS_SELECTOR, By.XPATH, etc.)
        
    Returns:
        True if the element exists, False otherwise
    """
    try:
        browser.find_element(by, selector)
        return True
    except NoSuchElementException:
        return False 
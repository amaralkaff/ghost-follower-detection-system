import time
import os
import pickle
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config.config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
from src.utils.browser import wait_for_element, random_sleep, element_exists
from src.utils.logger import get_default_logger

# Get logger
logger = get_default_logger()

# Instagram URLs
INSTAGRAM_URL = "https://www.instagram.com/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"

# Selectors
USERNAME_INPUT = "input[name='username']"
PASSWORD_INPUT = "input[name='password']"
LOGIN_BUTTON = "button[type='submit']"
SAVE_INFO_BUTTON = "//button[contains(text(), 'Save Info') or contains(text(), 'Not Now')]"
NOTIFICATIONS_BUTTON = "//button[contains(text(), 'Not Now')]"
TWO_FACTOR_INPUT = "input[name='verificationCode']"
TWO_FACTOR_BUTTON = "button[type='button']"
SUSPICIOUS_LOGIN_BUTTON = "//button[contains(text(), 'This Was Me')]"

def save_cookies(browser, username):
    """Save browser cookies to a file."""
    cookies_dir = "cookies"
    os.makedirs(cookies_dir, exist_ok=True)
    
    cookies_file = os.path.join(cookies_dir, f"{username}_cookies.pkl")
    pickle.dump(browser.get_cookies(), open(cookies_file, "wb"))
    logger.info(f"Cookies saved to {cookies_file}")

def load_cookies(browser, username):
    """Load cookies from file into browser."""
    cookies_file = os.path.join("cookies", f"{username}_cookies.pkl")
    
    if not os.path.exists(cookies_file):
        logger.info(f"No cookies file found for {username}")
        return False
    
    cookies = pickle.load(open(cookies_file, "rb"))
    for cookie in cookies:
        browser.add_cookie(cookie)
    
    logger.info(f"Cookies loaded from {cookies_file}")
    return True

def handle_two_factor_auth(browser):
    """Handle two-factor authentication if needed."""
    try:
        # Check if 2FA input is present
        two_factor_input = wait_for_element(browser, TWO_FACTOR_INPUT, timeout=5)
        
        if two_factor_input:
            logger.info("Two-factor authentication detected")
            
            # Ask user for verification code
            verification_code = input("Enter the verification code sent to your device: ")
            
            # Enter verification code
            two_factor_input.send_keys(verification_code)
            
            # Click confirm button
            two_factor_button = wait_for_element(browser, TWO_FACTOR_BUTTON)
            if two_factor_button:
                two_factor_button.click()
                random_sleep(3, 5)
                return True
            else:
                logger.error("Could not find two-factor confirmation button")
                return False
    except Exception as e:
        logger.info(f"No two-factor authentication required: {str(e)}")
    
    return True

def handle_suspicious_login(browser):
    """Handle suspicious login detection if needed."""
    try:
        # Check if suspicious login button is present
        suspicious_button = wait_for_element(browser, SUSPICIOUS_LOGIN_BUTTON, by=By.XPATH, timeout=5)
        
        if suspicious_button:
            logger.info("Suspicious login detected")
            suspicious_button.click()
            random_sleep(3, 5)
            return True
    except Exception as e:
        logger.info(f"No suspicious login detected: {str(e)}")
    
    return True

def handle_save_login_info(browser):
    """Handle 'Save Login Info' prompt if it appears."""
    try:
        # Check if save info button is present
        save_button = wait_for_element(browser, SAVE_INFO_BUTTON, by=By.XPATH, timeout=5)
        
        if save_button:
            logger.info("'Save Login Info' prompt detected")
            save_button.click()
            random_sleep(2, 4)
    except Exception as e:
        logger.info(f"No 'Save Login Info' prompt: {str(e)}")

def handle_notifications(browser):
    """Handle notifications prompt if it appears."""
    try:
        # Check if notifications button is present
        notifications_button = wait_for_element(browser, NOTIFICATIONS_BUTTON, by=By.XPATH, timeout=5)
        
        if notifications_button:
            logger.info("Notifications prompt detected")
            notifications_button.click()
            random_sleep(2, 4)
    except Exception as e:
        logger.info(f"No notifications prompt: {str(e)}")

def is_logged_in(browser):
    """Check if the user is logged in."""
    # Navigate to Instagram homepage
    browser.get(INSTAGRAM_URL)
    random_sleep(2, 4)
    
    # Check for elements that indicate logged-in state
    profile_icon = element_exists(browser, "span[role='link']")
    login_button = element_exists(browser, LOGIN_BUTTON)
    
    return profile_icon and not login_button

def login_to_instagram(browser):
    """
    Log in to Instagram using the provided credentials.
    
    Args:
        browser: The browser instance
        
    Returns:
        True if login successful, False otherwise
    """
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        logger.error("Instagram credentials not found in environment variables")
        return False
    
    logger.info(f"Attempting to log in as {INSTAGRAM_USERNAME}")
    
    # Try to use cookies first
    browser.get(INSTAGRAM_URL)
    if load_cookies(browser, INSTAGRAM_USERNAME):
        browser.refresh()
        random_sleep(3, 5)
        
        if is_logged_in(browser):
            logger.info("Successfully logged in using cookies")
            return True
        else:
            logger.info("Cookie login failed, trying with credentials")
    
    # Navigate to login page
    browser.get(LOGIN_URL)
    random_sleep(2, 4)
    
    # Enter username
    username_input = wait_for_element(browser, USERNAME_INPUT)
    if not username_input:
        logger.error("Could not find username input field")
        return False
    
    username_input.clear()
    username_input.send_keys(INSTAGRAM_USERNAME)
    random_sleep(1, 2)
    
    # Enter password
    password_input = wait_for_element(browser, PASSWORD_INPUT)
    if not password_input:
        logger.error("Could not find password input field")
        return False
    
    password_input.clear()
    password_input.send_keys(INSTAGRAM_PASSWORD)
    random_sleep(1, 2)
    
    # Click login button
    login_button = wait_for_element(browser, LOGIN_BUTTON)
    if not login_button:
        logger.error("Could not find login button")
        return False
    
    login_button.click()
    random_sleep(5, 7)
    
    # Handle two-factor authentication if needed
    if not handle_two_factor_auth(browser):
        logger.error("Two-factor authentication failed")
        return False
    
    # Handle suspicious login if needed
    if not handle_suspicious_login(browser):
        logger.error("Suspicious login handling failed")
        return False
    
    # Handle 'Save Login Info' prompt
    handle_save_login_info(browser)
    
    # Handle notifications prompt
    handle_notifications(browser)
    
    # Verify login success
    if is_logged_in(browser):
        logger.info("Successfully logged in to Instagram")
        
        # Save cookies for future use
        save_cookies(browser, INSTAGRAM_USERNAME)
        
        return True
    else:
        logger.error("Login failed")
        return False 
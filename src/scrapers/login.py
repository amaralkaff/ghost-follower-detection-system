import time
import os
import pickle
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config.config import INSTAGRAM_2FA_ENABLED
from src.utils.browser import wait_for_element, random_sleep, element_exists
from src.utils.logger import get_default_logger
from src.utils.credential_manager import CredentialManager

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
# Additional 2FA selectors
TWO_FACTOR_CODE_INPUT = "input[aria-label='Security code']"
TWO_FACTOR_CONFIRM_BUTTON = "//button[contains(text(), 'Confirm')]"
TWO_FACTOR_HEADER = "//h2[contains(text(), 'Enter Confirmation Code')]"
TWO_FACTOR_RESEND_BUTTON = "//button[contains(text(), 'Resend Code')]"

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

def handle_two_factor_auth(browser, two_factor_enabled=None):
    """
    Handle two-factor authentication if needed.
    
    This function checks for various 2FA UI elements that Instagram might show
    and handles the verification code input process.
    
    Args:
        browser: The browser instance
        two_factor_enabled: Override for 2FA setting (from credential manager)
        
    Returns:
        True if 2FA handled successfully or not needed, False otherwise
    """
    # Determine if 2FA is enabled
    if two_factor_enabled is None:
        two_factor_enabled = INSTAGRAM_2FA_ENABLED
        
    # If 2FA is disabled in config, skip the check
    if not two_factor_enabled:
        logger.info("2FA is disabled in config, skipping 2FA check")
        return True
        
    try:
        # Check for different possible 2FA indicators
        two_factor_header = element_exists(browser, TWO_FACTOR_HEADER, by=By.XPATH)
        two_factor_input1 = element_exists(browser, TWO_FACTOR_INPUT)
        two_factor_input2 = element_exists(browser, TWO_FACTOR_CODE_INPUT)
        
        if two_factor_header or two_factor_input1 or two_factor_input2:
            logger.info("Two-factor authentication detected")
            
            # Take a screenshot to help the user see what's happening
            screenshot_path = os.path.join("logs", "2fa_screen.png")
            browser.save_screenshot(screenshot_path)
            logger.info(f"2FA screen screenshot saved to {screenshot_path}")
            
            # Ask user for verification code
            verification_code = input("\n\n*** TWO-FACTOR AUTHENTICATION REQUIRED ***\nEnter the verification code sent to your device: ")
            
            # Try different input fields
            input_field = None
            if two_factor_input1:
                input_field = wait_for_element(browser, TWO_FACTOR_INPUT)
            elif two_factor_input2:
                input_field = wait_for_element(browser, TWO_FACTOR_CODE_INPUT)
            
            if not input_field:
                logger.error("Could not find 2FA input field")
                return False
            
            # Clear any existing text and enter verification code
            input_field.clear()
            input_field.send_keys(verification_code)
            random_sleep(1, 2)
            
            # Try different confirm buttons
            confirm_button = None
            if element_exists(browser, TWO_FACTOR_BUTTON):
                confirm_button = wait_for_element(browser, TWO_FACTOR_BUTTON)
            elif element_exists(browser, TWO_FACTOR_CONFIRM_BUTTON, by=By.XPATH):
                confirm_button = wait_for_element(browser, TWO_FACTOR_CONFIRM_BUTTON, by=By.XPATH)
            
            if confirm_button:
                confirm_button.click()
                logger.info("Submitted 2FA verification code")
                random_sleep(5, 7)  # Wait longer after 2FA submission
                
                # Check if 2FA was successful
                if element_exists(browser, TWO_FACTOR_HEADER, by=By.XPATH) or element_exists(browser, TWO_FACTOR_INPUT) or element_exists(browser, TWO_FACTOR_CODE_INPUT):
                    logger.error("2FA verification failed - incorrect code or expired")
                    
                    # Check if resend button is available
                    if element_exists(browser, TWO_FACTOR_RESEND_BUTTON, by=By.XPATH):
                        resend = input("Would you like to resend the code? (y/n): ").lower()
                        if resend == 'y':
                            resend_button = wait_for_element(browser, TWO_FACTOR_RESEND_BUTTON, by=By.XPATH)
                            if resend_button:
                                resend_button.click()
                                logger.info("Requested new 2FA code")
                                random_sleep(3, 5)
                                return handle_two_factor_auth(browser, two_factor_enabled)  # Recursive call to try again
                    
                    return False
                
                return True
            else:
                logger.error("Could not find 2FA confirmation button")
                return False
    except Exception as e:
        logger.info(f"Error during 2FA handling: {str(e)}")
    
    # If we reach here, either there was no 2FA or we couldn't detect it properly
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

def login_to_instagram(browser, use_encrypted_credentials=True, master_password=None):
    """
    Log in to Instagram using the provided credentials.
    
    Args:
        browser: The browser instance
        use_encrypted_credentials: Whether to use encrypted credentials
        master_password: Master password for decrypting credentials
        
    Returns:
        True if login successful, False otherwise
    """
    # Get credentials
    credential_manager = CredentialManager()
    
    if use_encrypted_credentials:
        # Set up encryption with master password
        if master_password:
            credential_manager.setup_encryption(master_password)
        else:
            # Try to set up encryption with default password
            if not credential_manager.setup_encryption():
                logger.error("Failed to set up credential encryption")
                return False
        
        # Get credentials
        credentials = credential_manager.get_credentials()
        if not credentials:
            logger.error("Could not retrieve Instagram credentials")
            return False
        
        username = credentials["username"]
        password = credentials["password"]
        two_factor_enabled = credentials["two_factor_enabled"]
    else:
        # Store credentials from environment variables for future use
        credential_manager.store_credentials_from_env()
        
        # Get credentials from environment variables
        credentials = credential_manager.get_credentials()
        if not credentials:
            logger.error("Instagram credentials not found in environment variables")
            return False
        
        username = credentials["username"]
        password = credentials["password"]
        two_factor_enabled = credentials["two_factor_enabled"]
    
    logger.info(f"Attempting to log in as {username}")
    logger.info(f"2FA is {'enabled' if two_factor_enabled else 'disabled'} in configuration")
    
    # Try to use cookies first
    browser.get(INSTAGRAM_URL)
    if load_cookies(browser, username):
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
    username_input.send_keys(username)
    random_sleep(1, 2)
    
    # Enter password
    password_input = wait_for_element(browser, PASSWORD_INPUT)
    if not password_input:
        logger.error("Could not find password input field")
        return False
    
    password_input.clear()
    password_input.send_keys(password)
    random_sleep(1, 2)
    
    # Click login button
    login_button = wait_for_element(browser, LOGIN_BUTTON)
    if not login_button:
        logger.error("Could not find login button")
        return False
    
    login_button.click()
    random_sleep(5, 7)
    
    # Handle two-factor authentication if needed
    if not handle_two_factor_auth(browser, two_factor_enabled):
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
        save_cookies(browser, username)
        
        return True
    else:
        logger.error("Login failed")
        
        # Take a screenshot of the failed login state
        screenshot_path = os.path.join("logs", "login_failed.png")
        browser.save_screenshot(screenshot_path)
        logger.info(f"Login failure screenshot saved to {screenshot_path}")
        
        return False 
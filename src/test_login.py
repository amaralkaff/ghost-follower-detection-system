#!/usr/bin/env python3
"""
Test script for Instagram login automation.
This script tests the secure credential storage and login functionality.
"""

import sys
import time
import os
import getpass
import pickle
import json
from pathlib import Path
from src.utils.browser import setup_browser
from src.utils.logger import get_default_logger
from src.scrapers.login import login_to_instagram
from src.utils.credential_manager import CredentialManager
from selenium.webdriver.common.by import By

def test_credential_manager():
    """Test the credential manager functionality."""
    logger = get_default_logger()
    logger.info("Testing credential manager...")
    
    credential_manager = CredentialManager()
    
    # Test setup encryption
    master_password = getpass.getpass("Enter a test master password: ")
    if not credential_manager.setup_encryption(master_password):
        logger.error("Failed to set up encryption")
        return False
    
    # Test storing credentials
    username = input("Enter a test username: ")
    password = getpass.getpass("Enter a test password: ")
    two_factor = input("Is 2FA enabled? (y/n): ").lower() == 'y'
    
    if not credential_manager.encrypt_credentials(username, password, two_factor):
        logger.error("Failed to encrypt credentials")
        return False
    
    # Test retrieving credentials
    credentials = credential_manager.get_credentials()
    if not credentials:
        logger.error("Failed to retrieve credentials")
        return False
    
    logger.info(f"Successfully retrieved credentials for {credentials['username']}")
    logger.info(f"2FA is {'enabled' if credentials['two_factor_enabled'] else 'disabled'}")
    
    return True

def test_auto_setup():
    """Test the automatic setup from environment variables."""
    logger = get_default_logger()
    logger.info("Testing automatic setup from environment variables...")
    
    # Check if required environment variables are set
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    master_password = os.getenv("MASTER_PASSWORD")
    
    if not username or not password:
        logger.error("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env file")
        return False
    
    if not master_password:
        logger.info("MASTER_PASSWORD not set in .env file, will use default")
    
    # Create a new credential manager
    credential_manager = CredentialManager()
    
    # Test auto setup
    if not credential_manager.auto_setup_from_env():
        logger.error("Failed to automatically set up credentials from environment")
        return False
    
    # Test retrieving credentials
    credentials = credential_manager.get_credentials()
    if not credentials:
        logger.error("Failed to retrieve credentials after auto setup")
        return False
    
    logger.info(f"Successfully auto-setup and retrieved credentials for {credentials['username']}")
    logger.info(f"2FA is {'enabled' if credentials['two_factor_enabled'] else 'disabled'}")
    
    return True

def test_login():
    """Test the Instagram login functionality."""
    logger = get_default_logger()
    logger.info("Testing Instagram login...")
    
    # Set up credential manager
    credential_manager = CredentialManager()
    
    # Try auto setup first
    if credential_manager.auto_setup_from_env():
        logger.info("Using automatically set up credentials from environment")
        master_password = os.getenv("MASTER_PASSWORD")
    else:
        # Manual setup
        master_password = getpass.getpass("Enter your master password: ")
        if not credential_manager.setup_encryption(master_password):
            logger.error("Failed to set up encryption")
            return False
    
    # Set up browser
    browser = setup_browser()
    
    try:
        # Attempt login
        if login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password):
            logger.info("Login successful!")
            
            # Keep browser open to verify
            logger.info("Keeping browser open for 10 seconds to verify login...")
            time.sleep(10)
            
            return True
        else:
            logger.error("Login failed")
            return False
    finally:
        # Clean up
        browser.quit()
        logger.info("Browser closed")

def test_cookie_handling():
    """Test cookie saving and loading functionality."""
    logger = get_default_logger()
    logger.info("Testing cookie handling...")
    
    # Set up credential manager
    credential_manager = CredentialManager()
    
    # Get credentials
    if credential_manager.auto_setup_from_env():
        logger.info("Using automatically set up credentials from environment")
        master_password = os.getenv("MASTER_PASSWORD")
    else:
        # Manual setup
        master_password = getpass.getpass("Enter your master password: ")
        if not credential_manager.setup_encryption(master_password):
            logger.error("Failed to set up encryption")
            return False
    
    credentials = credential_manager.get_credentials()
    if not credentials:
        logger.error("Failed to retrieve credentials")
        return False
    
    username = credentials["username"]
    
    # Create cookies directory if it doesn't exist
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / f"{username}_cookies.pkl"
    
    # Check if cookies already exist
    if cookie_file.exists():
        logger.info(f"Found existing cookies for {username}")
        
        # Test loading cookies
        browser = setup_browser()
        try:
            # First navigate to Instagram
            browser.get("https://www.instagram.com/")
            time.sleep(3)
            
            # Load cookies
            logger.info(f"Loading cookies from {cookie_file}")
            with open(cookie_file, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    # Handle domain issues that might cause cookie rejection
                    if "domain" in cookie and cookie["domain"].startswith("."):
                        cookie["domain"] = cookie["domain"][1:]
                    try:
                        browser.add_cookie(cookie)
                    except Exception as e:
                        logger.warning(f"Could not add cookie {cookie.get('name')}: {str(e)}")
            
            # Refresh the page to apply cookies
            browser.refresh()
            time.sleep(5)
            
            # Check if we're logged in
            if "not-logged-in" not in browser.page_source and username.lower() in browser.page_source.lower():
                logger.info("Successfully logged in using cookies!")
                
                # Verify by checking for profile elements
                try:
                    profile_link = browser.find_element(By.XPATH, f"//a[contains(@href, '/{username}/')]")
                    logger.info("Found profile link, confirming successful login")
                except:
                    logger.warning("Could not find profile link, but login might still be successful")
                
                # Keep browser open to verify
                logger.info("Keeping browser open for 10 seconds to verify login...")
                time.sleep(10)
                
                return True
            else:
                logger.warning("Cookies loaded but login unsuccessful")
                
                # Try regular login as fallback
                logger.info("Trying regular login as fallback...")
                if login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password):
                    logger.info("Fallback login successful!")
                    
                    # Save new cookies
                    logger.info(f"Saving new cookies to {cookie_file}")
                    with open(cookie_file, "wb") as f:
                        pickle.dump(browser.get_cookies(), f)
                    
                    return True
                else:
                    logger.error("Fallback login failed")
                    return False
        finally:
            browser.quit()
            logger.info("Browser closed")
    else:
        # No existing cookies, perform regular login and save cookies
        logger.info(f"No existing cookies found for {username}")
        browser = setup_browser()
        
        try:
            # Attempt login
            if login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password):
                logger.info("Login successful!")
                
                # Save cookies
                logger.info(f"Saving cookies to {cookie_file}")
                with open(cookie_file, "wb") as f:
                    pickle.dump(browser.get_cookies(), f)
                
                # Verify cookies were saved
                if cookie_file.exists():
                    logger.info("Cookies saved successfully")
                    
                    # Display cookie info
                    with open(cookie_file, "rb") as f:
                        cookies = pickle.load(f)
                        logger.info(f"Saved {len(cookies)} cookies")
                        
                        # Check for important cookies
                        session_id = next((c for c in cookies if c["name"] == "sessionid"), None)
                        ds_user_id = next((c for c in cookies if c["name"] == "ds_user_id"), None)
                        
                        if session_id and ds_user_id:
                            logger.info("Found essential cookies (sessionid and ds_user_id)")
                        else:
                            logger.warning("Missing some essential cookies")
                
                # Keep browser open to verify
                logger.info("Keeping browser open for 10 seconds to verify login...")
                time.sleep(10)
                
                return True
            else:
                logger.error("Login failed")
                return False
        finally:
            browser.quit()
            logger.info("Browser closed")

def test_cookie_expiration():
    """Test cookie expiration and refresh functionality."""
    logger = get_default_logger()
    logger.info("Testing cookie expiration and refresh...")
    
    # Set up credential manager
    credential_manager = CredentialManager()
    
    # Get credentials
    if credential_manager.auto_setup_from_env():
        logger.info("Using automatically set up credentials from environment")
        master_password = os.getenv("MASTER_PASSWORD")
    else:
        # Manual setup
        master_password = getpass.getpass("Enter your master password: ")
        if not credential_manager.setup_encryption(master_password):
            logger.error("Failed to set up encryption")
            return False
    
    credentials = credential_manager.get_credentials()
    if not credentials:
        logger.error("Failed to retrieve credentials")
        return False
    
    username = credentials["username"]
    
    # Create cookies directory if it doesn't exist
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / f"{username}_cookies.pkl"
    cookie_meta_file = cookies_dir / f"{username}_cookie_meta.json"
    
    # Check if cookies exist
    if cookie_file.exists():
        # Check cookie metadata if it exists
        if cookie_meta_file.exists():
            try:
                with open(cookie_meta_file, "r") as f:
                    meta = json.load(f)
                    last_updated = meta.get("last_updated", 0)
                    current_time = time.time()
                    
                    # Check if cookies are older than 3 days (259200 seconds)
                    if current_time - last_updated > 259200:
                        logger.info("Cookies are older than 3 days, refreshing...")
                        return refresh_cookies(username, master_password, cookie_file, cookie_meta_file)
                    else:
                        logger.info(f"Cookies are still valid (updated {(current_time - last_updated) / 86400:.1f} days ago)")
                        return test_cookie_validity(username, cookie_file, master_password)
            except Exception as e:
                logger.warning(f"Error reading cookie metadata: {str(e)}")
                return refresh_cookies(username, master_password, cookie_file, cookie_meta_file)
        else:
            # No metadata, create it
            logger.info("No cookie metadata found, creating and testing cookies...")
            
            # Test existing cookies first
            if test_cookie_validity(username, cookie_file, master_password):
                # Cookies are valid, create metadata
                with open(cookie_meta_file, "w") as f:
                    json.dump({"last_updated": time.time()}, f)
                return True
            else:
                # Cookies are invalid, refresh
                return refresh_cookies(username, master_password, cookie_file, cookie_meta_file)
    else:
        logger.info("No cookies found, creating new cookies...")
        return refresh_cookies(username, master_password, cookie_file, cookie_meta_file)

def test_cookie_validity(username, cookie_file, master_password):
    """Test if cookies are still valid."""
    logger = get_default_logger()
    logger.info("Testing cookie validity...")
    
    browser = setup_browser()
    try:
        # First navigate to Instagram
        browser.get("https://www.instagram.com/")
        time.sleep(3)
        
        # Load cookies
        logger.info(f"Loading cookies from {cookie_file}")
        with open(cookie_file, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                # Handle domain issues
                if "domain" in cookie and cookie["domain"].startswith("."):
                    cookie["domain"] = cookie["domain"][1:]
                try:
                    browser.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Could not add cookie {cookie.get('name')}: {str(e)}")
        
        # Refresh the page to apply cookies
        browser.refresh()
        time.sleep(5)
        
        # Check if we're logged in
        if "not-logged-in" not in browser.page_source and username.lower() in browser.page_source.lower():
            logger.info("Cookies are still valid!")
            return True
        else:
            logger.warning("Cookies are no longer valid")
            return False
    except Exception as e:
        logger.error(f"Error testing cookie validity: {str(e)}")
        return False
    finally:
        browser.quit()
        logger.info("Browser closed")

def refresh_cookies(username, master_password, cookie_file, cookie_meta_file):
    """Refresh cookies by logging in and saving new cookies."""
    logger = get_default_logger()
    logger.info("Refreshing cookies...")
    
    browser = setup_browser()
    try:
        # Attempt login
        if login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password):
            logger.info("Login successful!")
            
            # Save cookies
            logger.info(f"Saving cookies to {cookie_file}")
            with open(cookie_file, "wb") as f:
                pickle.dump(browser.get_cookies(), f)
            
            # Update metadata
            with open(cookie_meta_file, "w") as f:
                json.dump({"last_updated": time.time()}, f)
            
            logger.info("Cookies refreshed successfully")
            return True
        else:
            logger.error("Login failed, could not refresh cookies")
            return False
    finally:
        browser.quit()
        logger.info("Browser closed")

def main():
    """Main entry point for the test script."""
    logger = get_default_logger()
    logger.info("Starting login automation test")
    
    # Test options
    print("Select a test to run:")
    print("1. Test credential manager")
    print("2. Test Instagram login")
    print("3. Test auto setup from environment")
    print("4. Test cookie handling")
    print("5. Test cookie expiration and refresh")
    print("6. Run all tests")
    
    choice = input("Enter your choice (1-6): ")
    
    try:
        if choice == '1':
            if test_credential_manager():
                logger.info("Credential manager test passed")
                return 0
            else:
                logger.error("Credential manager test failed")
                return 1
        elif choice == '2':
            if test_login():
                logger.info("Login test passed")
                return 0
            else:
                logger.error("Login test failed")
                return 1
        elif choice == '3':
            if test_auto_setup():
                logger.info("Auto setup test passed")
                return 0
            else:
                logger.error("Auto setup test failed")
                return 1
        elif choice == '4':
            if test_cookie_handling():
                logger.info("Cookie handling test passed")
                return 0
            else:
                logger.error("Cookie handling test failed")
                return 1
        elif choice == '5':
            if test_cookie_expiration():
                logger.info("Cookie expiration test passed")
                return 0
            else:
                logger.error("Cookie expiration test failed")
                return 1
        elif choice == '6':
            cred_result = test_credential_manager()
            auto_result = test_auto_setup()
            login_result = test_login()
            cookie_result = test_cookie_handling()
            expiration_result = test_cookie_expiration()
            
            if cred_result and auto_result and login_result and cookie_result and expiration_result:
                logger.info("All tests passed")
                return 0
            else:
                logger.error("Some tests failed")
                return 1
        else:
            logger.error("Invalid choice")
            return 1
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python3
"""
Test script for Instagram login automation.
This script tests the secure credential storage and login functionality.
"""

import sys
import time
import os
import getpass
from src.utils.browser import setup_browser
from src.utils.logger import get_default_logger
from src.scrapers.login import login_to_instagram
from src.utils.credential_manager import CredentialManager

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

def main():
    """Main entry point for the test script."""
    logger = get_default_logger()
    logger.info("Starting login automation test")
    
    # Test options
    print("Select a test to run:")
    print("1. Test credential manager")
    print("2. Test Instagram login")
    print("3. Test auto setup from environment")
    print("4. Run all tests")
    
    choice = input("Enter your choice (1-4): ")
    
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
            cred_result = test_credential_manager()
            auto_result = test_auto_setup()
            login_result = test_login()
            
            if cred_result and auto_result and login_result:
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
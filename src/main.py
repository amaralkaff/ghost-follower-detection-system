import sys
import time
import os
import getpass
from src.utils.browser import setup_browser
from src.utils.logger import get_default_logger
from src.scrapers.login import login_to_instagram
from src.utils.credential_manager import CredentialManager

def setup_credentials():
    """Set up credentials for Instagram login."""
    logger = get_default_logger()
    credential_manager = CredentialManager()
    
    # Try automatic setup from environment variables first
    if credential_manager.auto_setup_from_env():
        logger.info("Credentials automatically set up from environment variables")
        return True, os.getenv("MASTER_PASSWORD")
    
    # Check if credentials file exists
    credentials_file = os.path.join("credentials", "encrypted_credentials.json")
    
    if os.path.exists(credentials_file):
        logger.info("Encrypted credentials file found")
        use_existing = input("Use existing encrypted credentials? (y/n): ").lower() == 'y'
        
        if use_existing:
            # Get master password
            master_password = getpass.getpass("Enter master password to decrypt credentials: ")
            if credential_manager.setup_encryption(master_password):
                credentials = credential_manager.get_credentials()
                if credentials:
                    logger.info(f"Successfully loaded credentials for {credentials['username']}")
                    return True, master_password
            
            logger.error("Failed to decrypt credentials")
            return False, None
    
    # No credentials file or user wants to create new one
    logger.info("Setting up new encrypted credentials")
    
    # Try to get credentials from environment variables
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    two_factor = os.getenv("INSTAGRAM_2FA_ENABLED", "True").lower() == 'true'
    
    # If not in environment, prompt user
    if not username:
        username = input("Enter Instagram username: ")
    if not password:
        password = getpass.getpass("Enter Instagram password: ")
    if os.getenv("INSTAGRAM_2FA_ENABLED") is None:
        two_factor = input("Is two-factor authentication enabled? (y/n): ").lower() == 'y'
    
    # Get master password for encryption
    master_password = os.getenv("MASTER_PASSWORD")
    if not master_password:
        master_password = getpass.getpass("Create a master password for credential encryption: ")
        confirm_password = getpass.getpass("Confirm master password: ")
        
        if master_password != confirm_password:
            logger.error("Passwords do not match")
            return False, None
    
    # Set up encryption
    if not credential_manager.setup_encryption(master_password):
        logger.error("Failed to set up encryption")
        return False, None
    
    # Encrypt and save credentials
    if credential_manager.encrypt_credentials(username, password, two_factor):
        logger.info(f"Credentials for {username} encrypted and saved successfully")
        return True, master_password
    
    logger.error("Failed to encrypt and save credentials")
    return False, None

def main():
    """Main entry point for the Instagram Ghost Follower Detection System."""
    # Get logger
    logger = get_default_logger()
    logger.info("Starting Instagram Ghost Follower Detection System")
    
    try:
        # Set up credentials
        credentials_setup, master_password = setup_credentials()
        if not credentials_setup:
            logger.error("Failed to set up credentials. Exiting.")
            return 1
        
        # Set up browser
        logger.info("Setting up browser")
        browser = setup_browser()
        
        # Log in to Instagram
        if not login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password):
            logger.error("Failed to log in to Instagram. Exiting.")
            browser.quit()
            return 1
        
        # Add more functionality here as the project progresses
        
        # Keep the browser open for a while to see the results
        logger.info("Login successful. Keeping browser open for 10 seconds.")
        time.sleep(10)
        
        # Clean up
        browser.quit()
        logger.info("Browser closed. Exiting.")
        return 0
        
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
import sys
import time
from src.utils.browser import setup_browser
from src.utils.logger import get_default_logger
from src.scrapers.login import login_to_instagram

def main():
    """Main entry point for the Instagram Ghost Follower Detection System."""
    # Get logger
    logger = get_default_logger()
    logger.info("Starting Instagram Ghost Follower Detection System")
    
    try:
        # Set up browser
        logger.info("Setting up browser")
        browser = setup_browser()
        
        # Log in to Instagram
        if not login_to_instagram(browser):
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
import os
import sys
import time
import json
from src.utils.browser import setup_browser
from src.utils.logger import get_default_logger
from src.scrapers.login import login_to_instagram
from src.utils.credential_manager import CredentialManager
from src.scrapers.engagement_scraper import EngagementScraper
from src.data.engagement_data import EngagementDataProcessor

# Get logger
logger = get_default_logger()

def test_engagement_scraper(target_username=None):
    """
    Test the engagement scraper functionality.
    
    Args:
        target_username: Target username to analyze (if None, uses logged-in user)
    """
    logger.info("Starting engagement scraper test")
    
    # Set up credentials
    credential_manager = CredentialManager()
    
    # Try automatic setup from environment variables first
    if credential_manager.auto_setup_from_env():
        logger.info("Credentials automatically set up from environment variables")
        master_password = os.getenv("MASTER_PASSWORD")
    else:
        # Use manual input for testing
        logger.info("Enter credentials for testing:")
        username = input("Instagram username: ")
        password = input("Instagram password: ")
        master_password = "test_password"
        
        # Set up credentials
        credential_manager.set_credentials(username, password)
        credential_manager.setup_encryption(master_password)
    
    # Set up browser
    browser = setup_browser()
    if not browser:
        logger.error("Failed to set up browser. Exiting.")
        return
    
    try:
        # Login to Instagram
        login_successful = login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password)
        
        if not login_successful:
            logger.error("Login failed. Exiting.")
            return
        
        logger.info("Login successful")
        
        # Initialize engagement scraper
        engagement_scraper = EngagementScraper(target_username)
        engagement_scraper.set_browser(browser)  # Use existing browser instance
        
        # Run the scraper
        engagement_data = engagement_scraper.run()
        
        if engagement_data:
            logger.info("Engagement data collection completed successfully")
            
            # Print some stats
            post_count = len(engagement_data.get('post_engagement', []))
            story_count = len(engagement_data.get('story_engagement', []))
            reel_count = len(engagement_data.get('reel_engagement', []))
            activity_count = len(engagement_data.get('online_activity', []))
            
            logger.info(f"Collected data for {post_count} posts, {story_count} stories, {reel_count} reels")
            logger.info(f"Collected {activity_count} online activity records")
            
            # Test engagement data processor
            logger.info("Testing engagement data processor")
            processor = EngagementDataProcessor(target_username or engagement_scraper.username)
            
            # Load data
            if processor.load_data():
                logger.info("Data loaded successfully")
                
                # Calculate engagement metrics
                if processor.calculate_engagement_metrics():
                    logger.info("Engagement metrics calculated successfully")
                    
                    # Identify ghost followers
                    ghost_followers = processor.identify_ghost_followers()
                    ghost_count = len(ghost_followers.get('ghost_followers', {}))
                    active_count = len(ghost_followers.get('active_followers', {}))
                    
                    logger.info(f"Identified {ghost_count} ghost followers and {active_count} active followers")
                    
                    # Categorize ghost followers
                    categorized = processor.categorize_ghost_followers()
                    definite_count = len(categorized.get('definite_ghosts', {}))
                    probable_count = len(categorized.get('probable_ghosts', {}))
                    possible_count = len(categorized.get('possible_ghosts', {}))
                    
                    logger.info(f"Categorized as: {definite_count} definite, {probable_count} probable, {possible_count} possible")
                    
                    # Export data
                    export_files = processor.export_engagement_data()
                    if export_files:
                        logger.info(f"Data exported to: {', '.join(export_files.values())}")
                    else:
                        logger.warning("Data export failed")
                else:
                    logger.error("Failed to calculate engagement metrics")
            else:
                logger.error("Failed to load data")
        else:
            logger.error("Failed to collect engagement data")
            
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        # Close the browser
        if browser:
            browser.quit()
            logger.info("Browser closed")

if __name__ == "__main__":
    # Get target username from command line argument if provided
    target_username = sys.argv[1] if len(sys.argv) > 1 else None
    test_engagement_scraper(target_username) 
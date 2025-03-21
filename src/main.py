import sys
import time
import os
import getpass
import argparse
from src.utils.browser import setup_browser
from src.utils.logger import get_default_logger
from src.scrapers.login import login_to_instagram
from src.utils.credential_manager import CredentialManager
from src.scrapers.follower_scraper import FollowerScraper
from src.scrapers.engagement_scraper import EngagementScraper
from src.data.follower_data import FollowerDataManager
from src.data.engagement_data import EngagementDataProcessor
from datetime import datetime
from src.utils.human_behavior import HumanBehaviorSimulator

# Get logger
logger = get_default_logger()

def setup_credentials():
    """Set up credentials for Instagram login."""
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
    if two_factor is None:
        two_factor = input("Is two-factor authentication enabled? (y/n): ").lower() == 'y'
    
    # Create master password for encryption
    master_password = getpass.getpass("Create a master password for credential encryption: ")
    master_password_confirm = getpass.getpass("Confirm master password: ")
    
    if master_password != master_password_confirm:
        logger.error("Master passwords do not match")
        return False, None
    
    # Set up encryption and save credentials
    if credential_manager.setup_encryption(master_password):
        credential_manager.save_credentials(username, password, two_factor)
        logger.info("Credentials encrypted and saved successfully")
        return True, master_password
    
    logger.error("Failed to set up credential encryption")
    return False, None

def collect_follower_data(browser, target_username=None, skip_profile_analysis=True):
    """
    Collect follower data using the follower scraper.
    
    Args:
        browser: Selenium WebDriver instance
        target_username: Username to collect followers for (if None, uses logged-in user)
        skip_profile_analysis: If True, only collect basic follower data without analyzing profiles
    
    Returns:
        List of follower data dictionaries
    """
    logger.info("Starting follower data collection")
    
    # Initialize follower scraper
    follower_scraper = FollowerScraper(target_username)
    follower_scraper.browser = browser
    # Set flag to indicate browser was passed externally
    follower_scraper._browser_passed_externally = True
    # Set flag to skip profile analysis if requested
    follower_scraper.skip_profile_analysis = skip_profile_analysis
    
    try:
        # Run the scraper
        followers_data = follower_scraper.run()
        
        # Process and save the data
        data_manager = FollowerDataManager()
        
        # Export to CSV for easy analysis
        if followers_data:
            data_manager.export_to_csv({
                "target_username": follower_scraper.target_username,
                "collection_timestamp": datetime.now().isoformat(),
                "total_followers_collected": len(followers_data),
                "followers": followers_data
            })
        
        return followers_data
        
    except Exception as e:
        logger.error(f"Error collecting follower data: {str(e)}")
        return None

def collect_engagement_data(browser, target_username=None):
    """
    Collect engagement data using the EngagementScraper.
    
    Args:
        browser: Selenium browser instance
        target_username: Target username to analyze (if None, uses logged-in user)
        
    Returns:
        Dictionary containing engagement data or None on failure
    """
    logger.info(f"Starting engagement data collection for {target_username or 'logged-in user'}")
    
    try:
        # Initialize engagement scraper
        engagement_scraper = EngagementScraper(target_username)
        engagement_scraper.set_browser(browser)  # Use existing browser instance
        
        # Run the scraper
        engagement_data = engagement_scraper.run()
        
        if engagement_data:
            logger.info("Engagement data collection completed successfully")
            return engagement_data
        else:
            logger.error("Failed to collect engagement data")
            return None
            
    except Exception as e:
        logger.error(f"Error collecting engagement data: {str(e)}")
        return None

def analyze_engagement_data(target_username=None):
    """
    Analyze engagement data and identify ghost followers.
    
    Args:
        target_username: Target username to analyze (if None, uses logged-in user)
        
    Returns:
        Dictionary containing analysis results or None on failure
    """
    logger.info(f"Starting engagement data analysis for {target_username or 'logged-in user'}")
    
    try:
        # Initialize engagement data processor
        processor = EngagementDataProcessor(target_username)
        
        # Load data
        if not processor.load_data():
            logger.error("Failed to load engagement data")
            return None
        
        # Calculate engagement metrics
        if not processor.calculate_engagement_metrics():
            logger.error("Failed to calculate engagement metrics")
            return None
        
        # Identify ghost followers
        ghost_followers = processor.identify_ghost_followers()
        
        # Categorize ghost followers
        categorized_ghosts = processor.categorize_ghost_followers()
        
        # Export data to CSV
        export_files = processor.export_engagement_data()
        
        logger.info("Engagement data analysis completed successfully")
        
        return {
            'ghost_followers': ghost_followers,
            'categorized_ghosts': categorized_ghosts,
            'export_files': export_files
        }
        
    except Exception as e:
        logger.error(f"Error analyzing engagement data: {str(e)}")
        return None

def main():
    """Main entry point for the application."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Instagram Ghost Follower Detection System")
    parser.add_argument("--target", "-t", help="Target username to analyze (if not provided, uses logged-in user)")
    parser.add_argument("--collect-followers", action="store_true", help="Collect follower data")
    parser.add_argument("--collect-engagement", action="store_true", help="Collect engagement data")
    parser.add_argument("--analyze-engagement", action="store_true", help="Analyze engagement data")
    parser.add_argument("--detect-ghosts", action="store_true", help="Detect ghost followers")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    parser.add_argument("--simulate", action="store_true", help="Simulate engagement data instead of collecting it")
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Check if only simulation and analysis are requested
    simulation_only = args.simulate and (args.analyze_engagement or args.detect_ghosts) and not (args.collect_followers or args.collect_engagement)
    
    # Set up credentials (skip if only simulation and analysis are requested)
    if not simulation_only:
        credentials_setup, master_password = setup_credentials()
        if not credentials_setup:
            logger.error("Failed to set up credentials. Exiting.")
            return
        
        # Set up browser
        browser = setup_browser()
        if not browser:
            logger.error("Failed to set up browser. Exiting.")
            return
    else:
        browser = None
        master_password = None
    
    try:
        # Login to Instagram (skip if only simulation and analysis are requested)
        if not simulation_only:
            login_successful = login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password)
            
            if not login_successful:
                logger.error("Login failed. Exiting.")
                return
            
            logger.info("Login successful")
        
        # Determine which steps to run
        run_all = args.all
        collect_followers = args.collect_followers or run_all
        collect_engagement = args.collect_engagement or run_all
        analyze_engagement = args.analyze_engagement or run_all
        detect_ghosts = args.detect_ghosts or run_all
        generate_report = args.report or run_all
        simulate = args.simulate
        
        # Get target username
        target_username = args.target
        
        # Collect follower data if requested
        if collect_followers and browser:
            followers_data = collect_follower_data(browser, target_username)
            if not followers_data:
                logger.warning("No follower data collected")
        
        # Collect or simulate engagement data if requested
        if collect_engagement:
            if simulate:
                # Simulate engagement data
                logger.info(f"Simulating engagement data for {target_username}")
                engagement_scraper = EngagementScraper(target_username)
                engagement_data = engagement_scraper.simulate_engagement_data()
                if not engagement_data:
                    logger.warning("Failed to simulate engagement data")
            elif browser:
                # Collect real engagement data
                engagement_data = collect_engagement_data(browser, target_username)
                if not engagement_data:
                    logger.warning("No engagement data collected")
        elif simulate and not collect_engagement:
            # If --simulate is specified without --collect-engagement
            logger.info(f"Simulating engagement data for {target_username}")
            engagement_scraper = EngagementScraper(target_username)
            engagement_data = engagement_scraper.simulate_engagement_data()
            if not engagement_data:
                logger.warning("Failed to simulate engagement data")
        
        # Analyze engagement data if requested
        if analyze_engagement:
            analysis_results = analyze_engagement_data(target_username)
            if not analysis_results:
                logger.warning("Engagement analysis failed")
            else:
                # Log some basic stats
                ghost_followers = analysis_results.get('ghost_followers', {}).get('ghost_followers', {})
                categorized = analysis_results.get('categorized_ghosts', {})
                
                logger.info(f"Found {len(ghost_followers)} ghost followers")
                logger.info(f"Categorized as: {len(categorized.get('definite_ghosts', {}))} definite, "
                           f"{len(categorized.get('probable_ghosts', {}))} probable, "
                           f"{len(categorized.get('possible_ghosts', {}))} possible")
        
        # Detect ghost followers if requested
        if detect_ghosts and not analyze_engagement:
            # If analyze_engagement was not run, run it now
            analysis_results = analyze_engagement_data(target_username)
            if not analysis_results:
                logger.warning("Ghost follower detection failed")
        
        # Generate report if requested
        if generate_report:
            # Placeholder for report generation
            logger.info("Report generation not yet implemented")
        
        logger.info("All requested operations completed")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        # Close the browser
        if browser:
            browser.quit()
            logger.info("Browser closed")

if __name__ == "__main__":
    main() 
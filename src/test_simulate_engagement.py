import os
import sys
from src.utils.logger import get_default_logger
from src.scrapers.engagement_scraper import EngagementScraper
from src.data.engagement_data import EngagementDataProcessor

# Get logger
logger = get_default_logger()

def test_simulate_engagement(target_username=None):
    """
    Test the simulate_engagement_data functionality.
    
    Args:
        target_username: Target username to analyze (if None, uses logged-in user)
    """
    logger.info("Starting engagement simulation test")
    
    if not target_username:
        target_username = "amaralkaff"  # Default username
    
    try:
        # Initialize engagement scraper
        engagement_scraper = EngagementScraper(target_username)
        
        # Simulate engagement data
        success = engagement_scraper.simulate_engagement_data()
        
        if success:
            logger.info("Engagement data simulation completed successfully")
            
            # Test engagement data processor
            logger.info("Testing engagement data processor with simulated data")
            processor = EngagementDataProcessor(target_username)
            
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
            logger.error("Failed to simulate engagement data")
            
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Get target username from command line argument if provided
    target_username = sys.argv[1] if len(sys.argv) > 1 else None
    test_simulate_engagement(target_username) 
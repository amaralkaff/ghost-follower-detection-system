import os
import json
import pandas as pd
from datetime import datetime
from src.utils.logger import get_default_logger

# Get logger
logger = get_default_logger()

class FollowerDataManager:
    """
    Manages follower data storage, retrieval, and processing.
    Provides methods for working with follower data collected by the scraper.
    """
    
    def __init__(self):
        """Initialize the follower data manager."""
        self.data_dir = os.path.join("data", "followers")
        os.makedirs(self.data_dir, exist_ok=True)
    
    def save_follower_data(self, target_username, followers_data):
        """
        Save follower data to a JSON file.
        
        Args:
            target_username: Username of the account whose followers were collected
            followers_data: List of follower data dictionaries
        
        Returns:
            Path to the saved file
        """
        if not followers_data:
            logger.warning("No follower data to save")
            return None
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_username}_followers_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        # Save to JSON file
        with open(filepath, "w") as f:
            json.dump({
                "target_username": target_username,
                "collection_timestamp": datetime.now().isoformat(),
                "total_followers_collected": len(followers_data),
                "followers": followers_data
            }, f, indent=2)
        
        logger.info(f"Follower data saved to {filepath}")
        return filepath
    
    def load_follower_data(self, filepath=None, target_username=None, latest=True):
        """
        Load follower data from a JSON file.
        
        Args:
            filepath: Path to the specific JSON file to load
            target_username: Username to filter files by
            latest: Whether to load the latest file for the target username
        
        Returns:
            Dictionary with follower data
        """
        # If filepath is provided, load that specific file
        if filepath and os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
        
        # Otherwise, find files for the target username
        if target_username:
            files = [f for f in os.listdir(self.data_dir) 
                    if f.startswith(f"{target_username}_followers_") and f.endswith(".json")]
            
            if not files:
                logger.warning(f"No follower data files found for {target_username}")
                return None
            
            # Sort files by timestamp (newest first)
            files.sort(reverse=True)
            
            # Load the latest file or all files
            if latest:
                filepath = os.path.join(self.data_dir, files[0])
                with open(filepath, "r") as f:
                    return json.load(f)
            else:
                # Load all files and merge data
                all_data = []
                for file in files:
                    filepath = os.path.join(self.data_dir, file)
                    with open(filepath, "r") as f:
                        all_data.append(json.load(f))
                return all_data
        
        logger.warning("No filepath or target_username provided")
        return None
    
    def convert_to_dataframe(self, follower_data):
        """
        Convert follower data to a pandas DataFrame for analysis.
        
        Args:
            follower_data: Dictionary with follower data
        
        Returns:
            Pandas DataFrame
        """
        if not follower_data or "followers" not in follower_data:
            logger.warning("Invalid follower data format")
            return None
        
        # Create DataFrame from followers list
        df = pd.DataFrame(follower_data["followers"])
        
        # Add metadata as columns
        df["target_username"] = follower_data["target_username"]
        df["collection_timestamp"] = follower_data["collection_timestamp"]
        
        return df
    
    def merge_follower_data(self, target_username):
        """
        Merge all follower data files for a target username.
        
        Args:
            target_username: Username to merge files for
        
        Returns:
            Merged follower data dictionary
        """
        # Load all data files for the target username
        all_data = self.load_follower_data(target_username=target_username, latest=False)
        
        if not all_data or not isinstance(all_data, list):
            return None
        
        # Initialize merged data
        merged_data = {
            "target_username": target_username,
            "collection_timestamp": datetime.now().isoformat(),
            "total_followers_collected": 0,
            "followers": []
        }
        
        # Track usernames to avoid duplicates
        usernames_seen = set()
        
        # Merge followers from all files
        for data in all_data:
            if "followers" not in data:
                continue
                
            for follower in data["followers"]:
                if "username" not in follower:
                    continue
                    
                username = follower["username"]
                
                if username not in usernames_seen:
                    merged_data["followers"].append(follower)
                    usernames_seen.add(username)
        
        # Update total count
        merged_data["total_followers_collected"] = len(merged_data["followers"])
        
        # Save merged data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_username}_followers_merged_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(merged_data, f, indent=2)
        
        logger.info(f"Merged follower data saved to {filepath}")
        return merged_data
    
    def export_to_csv(self, follower_data, filepath=None):
        """
        Export follower data to a CSV file.
        
        Args:
            follower_data: Dictionary with follower data
            filepath: Path to save the CSV file (optional)
        
        Returns:
            Path to the saved CSV file
        """
        # Convert to DataFrame
        df = self.convert_to_dataframe(follower_data)
        
        if df is None:
            return None
        
        # Create default filepath if not provided
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{follower_data['target_username']}_followers_{timestamp}.csv"
            filepath = os.path.join(self.data_dir, filename)
        
        # Export to CSV
        df.to_csv(filepath, index=False)
        logger.info(f"Follower data exported to CSV: {filepath}")
        
        return filepath
    
    def get_follower_statistics(self, follower_data):
        """
        Calculate statistics about the follower data.
        
        Args:
            follower_data: Dictionary with follower data
        
        Returns:
            Dictionary with statistics
        """
        if not follower_data or "followers" not in follower_data:
            return None
        
        followers = follower_data["followers"]
        
        # Initialize statistics
        stats = {
            "total_followers": len(followers),
            "analyzed_profiles": sum(1 for f in followers if f.get("detailed_profile_analyzed", False)),
            "account_types": {
                "personal": 0,
                "business": 0,
                "creator": 0,
                "unknown": 0
            },
            "privacy_status": {
                "private": 0,
                "public": 0
            },
            "potential_bots": 0,
            "high_follower_accounts": 0,
            "low_engagement_potential": 0,
            "avg_followers": 0,
            "avg_following": 0,
            "avg_posts": 0
        }
        
        # Calculate statistics
        analyzed_count = 0
        total_followers = 0
        total_following = 0
        total_posts = 0
        
        for follower in followers:
            # Skip followers without detailed analysis for some metrics
            if follower.get("detailed_profile_analyzed", False):
                analyzed_count += 1
                
                # Account type
                account_type = follower.get("account_type", "unknown")
                stats["account_types"][account_type] += 1
                
                # Privacy status
                if follower.get("is_private", False):
                    stats["privacy_status"]["private"] += 1
                else:
                    stats["privacy_status"]["public"] += 1
                
                # Follower metrics
                followers_count = follower.get("followers_count", 0)
                following_count = follower.get("following_count", 0)
                posts_count = follower.get("posts_count", 0)
                
                total_followers += followers_count
                total_following += following_count
                total_posts += posts_count
                
                # High follower accounts
                if followers_count > 10000:
                    stats["high_follower_accounts"] += 1
                
                # Low engagement potential
                if (following_count > 1000 and 
                    (followers_count < 100 or (following_count / max(followers_count, 1)) > 10) and
                    posts_count < 10):
                    stats["low_engagement_potential"] += 1
            
            # Check for potential bots based on username patterns
            username = follower["username"].lower()
            if (any(pattern in username for pattern in ["bot", "follow", "gram", "like"]) or
                (username.isalnum() and len(username) >= 10 and any(c.isdigit() for c in username))):
                stats["potential_bots"] += 1
        
        # Calculate averages
        if analyzed_count > 0:
            stats["avg_followers"] = total_followers / analyzed_count
            stats["avg_following"] = total_following / analyzed_count
            stats["avg_posts"] = total_posts / analyzed_count
        
        return stats 
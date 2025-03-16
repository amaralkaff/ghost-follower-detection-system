import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.utils.logger import get_default_logger

# Get logger
logger = get_default_logger()

class EngagementDataProcessor:
    """
    Processes and analyzes engagement data collected from Instagram.
    Calculates engagement metrics and identifies ghost followers.
    """
    
    def __init__(self, username):
        """
        Initialize the engagement data processor.
        
        Args:
            username: The username whose engagement data to process
        """
        self.username = username
        self.data_dir = "data"
        self.followers_data = None
        self.post_engagement_data = None
        self.story_engagement_data = None
        self.reel_engagement_data = None
        self.online_activity_data = None
        self.engagement_metrics = {}
        
    def load_data(self):
        """Load all engagement and follower data from JSON files."""
        try:
            # Load followers data
            followers_file = os.path.join(self.data_dir, f"{self.username}_followers.json")
            
            # If not found in regular data directory, try data/followers directory
            if not os.path.exists(followers_file):
                followers_dir = os.path.join("data", "followers")
                if os.path.exists(followers_dir):
                    # Find the most recent followers file
                    follower_files = []
                    for filename in os.listdir(followers_dir):
                        if filename.startswith(f"{self.username}_followers_") and filename.endswith(".json"):
                            file_path = os.path.join(followers_dir, filename)
                            # Get file modification time
                            mod_time = os.path.getmtime(file_path)
                            follower_files.append((file_path, mod_time))
                    
                    if follower_files:
                        # Sort by modification time (newest first)
                        follower_files.sort(key=lambda x: x[1], reverse=True)
                        followers_file = follower_files[0][0]
            
            if os.path.exists(followers_file):
                with open(followers_file, 'r') as f:
                    data = json.load(f)
                
                # Check if the data is a dictionary with a 'followers' key
                if isinstance(data, dict) and 'followers' in data:
                    self.followers_data = data['followers']
                else:
                    # Otherwise, assume it's a list of followers
                    self.followers_data = data
                
                logger.info(f"Loaded {len(self.followers_data)} followers from {followers_file}")
            else:
                logger.warning(f"Followers data file not found: {followers_file}")
            
            # Load post engagement data
            post_file = os.path.join(self.data_dir, f"{self.username}_post_engagement.json")
            if os.path.exists(post_file):
                with open(post_file, 'r') as f:
                    self.post_engagement_data = json.load(f)
                logger.info(f"Loaded {len(self.post_engagement_data)} posts from {post_file}")
            else:
                logger.warning(f"Post engagement data file not found: {post_file}")
            
            # Load story engagement data
            story_file = os.path.join(self.data_dir, f"{self.username}_story_engagement.json")
            if os.path.exists(story_file):
                with open(story_file, 'r') as f:
                    self.story_engagement_data = json.load(f)
                logger.info(f"Loaded {len(self.story_engagement_data)} stories from {story_file}")
            else:
                logger.warning(f"Story engagement data file not found: {story_file}")
            
            # Load reel engagement data
            reel_file = os.path.join(self.data_dir, f"{self.username}_reel_engagement.json")
            if os.path.exists(reel_file):
                with open(reel_file, 'r') as f:
                    self.reel_engagement_data = json.load(f)
                logger.info(f"Loaded {len(self.reel_engagement_data)} reels from {reel_file}")
            else:
                logger.warning(f"Reel engagement data file not found: {reel_file}")
            
            # Load online activity data
            activity_file = os.path.join(self.data_dir, f"{self.username}_online_activity.json")
            if os.path.exists(activity_file):
                with open(activity_file, 'r') as f:
                    self.online_activity_data = json.load(f)
                logger.info(f"Loaded {len(self.online_activity_data)} activity records from {activity_file}")
            else:
                logger.warning(f"Online activity data file not found: {activity_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading engagement data: {str(e)}")
            return False
    
    def calculate_engagement_metrics(self):
        """
        Calculate engagement metrics for each follower.
        Metrics include like ratio, comment frequency, story view rate, etc.
        """
        logger.info("Calculating engagement metrics for followers")
        
        if not self.followers_data:
            logger.error("No followers data available")
            return False
        
        # Initialize metrics dictionary
        for follower in self.followers_data:
            username = follower.get('username')
            if not username:
                continue
                
            self.engagement_metrics[username] = {
                'like_count': 0,
                'comment_count': 0,
                'story_view_count': 0,
                'reel_engagement_count': 0,
                'active_now_count': 0,
                'posts_seen': 0,
                'stories_seen': 0,
                'reels_seen': 0,
                'activity_checks': 0,
                'last_engagement': None,
                'engagement_score': 0.0
            }
        
        # Process post engagement data
        if self.post_engagement_data:
            for post in self.post_engagement_data:
                # Process likes
                likes = post.get('likes', {})
                usernames = likes.get('usernames', [])
                
                for username in usernames:
                    if username in self.engagement_metrics:
                        self.engagement_metrics[username]['like_count'] += 1
                        self.engagement_metrics[username]['posts_seen'] += 1
                        
                        # Update last engagement timestamp
                        post_timestamp = post.get('timestamp')
                        if post_timestamp:
                            if not self.engagement_metrics[username]['last_engagement'] or \
                               post_timestamp > self.engagement_metrics[username]['last_engagement']:
                                self.engagement_metrics[username]['last_engagement'] = post_timestamp
                
                # Process comments
                comments = post.get('comments', {})
                comment_list = comments.get('comments', [])
                
                for comment in comment_list:
                    username = comment.get('username')
                    if username in self.engagement_metrics:
                        self.engagement_metrics[username]['comment_count'] += 1
                        self.engagement_metrics[username]['posts_seen'] += 1
                        
                        # Update last engagement timestamp
                        post_timestamp = post.get('timestamp')
                        if post_timestamp:
                            if not self.engagement_metrics[username]['last_engagement'] or \
                               post_timestamp > self.engagement_metrics[username]['last_engagement']:
                                self.engagement_metrics[username]['last_engagement'] = post_timestamp
        
        # Process story engagement data
        if self.story_engagement_data:
            for story in self.story_engagement_data:
                viewers = story.get('viewers', [])
                
                for username in viewers:
                    if username in self.engagement_metrics:
                        self.engagement_metrics[username]['story_view_count'] += 1
                        self.engagement_metrics[username]['stories_seen'] += 1
                        
                        # Update last engagement timestamp
                        story_timestamp = story.get('timestamp')
                        if story_timestamp:
                            if not self.engagement_metrics[username]['last_engagement'] or \
                               story_timestamp > self.engagement_metrics[username]['last_engagement']:
                                self.engagement_metrics[username]['last_engagement'] = story_timestamp
        
        # Process reel engagement data
        if self.reel_engagement_data:
            for reel in self.reel_engagement_data:
                # Process likes
                likes = reel.get('likes', {})
                usernames = likes.get('usernames', [])
                
                for username in usernames:
                    if username in self.engagement_metrics:
                        self.engagement_metrics[username]['reel_engagement_count'] += 1
                        self.engagement_metrics[username]['reels_seen'] += 1
                        
                        # Update last engagement timestamp
                        reel_timestamp = reel.get('timestamp')
                        if reel_timestamp:
                            if not self.engagement_metrics[username]['last_engagement'] or \
                               reel_timestamp > self.engagement_metrics[username]['last_engagement']:
                                self.engagement_metrics[username]['last_engagement'] = reel_timestamp
                
                # Process comments
                comments = reel.get('comments', {})
                comment_list = comments.get('comments', [])
                
                for comment in comment_list:
                    username = comment.get('username')
                    if username in self.engagement_metrics:
                        self.engagement_metrics[username]['reel_engagement_count'] += 1
                        self.engagement_metrics[username]['reels_seen'] += 1
                        
                        # Update last engagement timestamp
                        reel_timestamp = reel.get('timestamp')
                        if reel_timestamp:
                            if not self.engagement_metrics[username]['last_engagement'] or \
                               reel_timestamp > self.engagement_metrics[username]['last_engagement']:
                                self.engagement_metrics[username]['last_engagement'] = reel_timestamp
        
        # Process online activity data
        if self.online_activity_data:
            for activity in self.online_activity_data:
                username = activity.get('username')
                is_active = activity.get('is_active', False)
                
                if username in self.engagement_metrics:
                    self.engagement_metrics[username]['activity_checks'] += 1
                    
                    if is_active:
                        self.engagement_metrics[username]['active_now_count'] += 1
                        
                        # Update last engagement timestamp
                        activity_timestamp = activity.get('timestamp')
                        if activity_timestamp:
                            if not self.engagement_metrics[username]['last_engagement'] or \
                               activity_timestamp > self.engagement_metrics[username]['last_engagement']:
                                self.engagement_metrics[username]['last_engagement'] = activity_timestamp
        
        # Calculate overall engagement score for each follower
        for username, metrics in self.engagement_metrics.items():
            # Calculate engagement rates
            posts_seen = max(1, metrics['posts_seen'])  # Avoid division by zero
            stories_seen = max(1, metrics['stories_seen'])
            reels_seen = max(1, metrics['reels_seen'])
            activity_checks = max(1, metrics['activity_checks'])
            
            like_rate = metrics['like_count'] / posts_seen
            comment_rate = metrics['comment_count'] / posts_seen
            story_view_rate = metrics['story_view_count'] / stories_seen
            reel_engagement_rate = metrics['reel_engagement_count'] / reels_seen
            active_rate = metrics['active_now_count'] / activity_checks
            
            # Calculate recency factor (higher if engaged recently)
            recency_factor = 1.0
            if metrics['last_engagement']:
                last_engagement = datetime.fromisoformat(metrics['last_engagement'])
                now = datetime.now()
                days_since_engagement = (now - last_engagement).days
                
                # Exponential decay based on days since last engagement
                recency_factor = np.exp(-0.1 * days_since_engagement)
            
            # Calculate overall engagement score (weighted average of all metrics)
            engagement_score = (
                0.3 * like_rate +
                0.3 * comment_rate +
                0.2 * story_view_rate +
                0.1 * reel_engagement_rate +
                0.1 * active_rate
            ) * recency_factor
            
            # Update engagement score
            self.engagement_metrics[username]['engagement_score'] = engagement_score
        
        logger.info(f"Calculated engagement metrics for {len(self.engagement_metrics)} followers")
        return True
    
    def identify_ghost_followers(self, threshold=0.1):
        """
        Identify ghost followers based on engagement metrics.
        
        Args:
            threshold: Engagement score threshold below which a follower is considered a ghost
            
        Returns:
            Dictionary of ghost followers with their metrics
        """
        logger.info(f"Identifying ghost followers with threshold {threshold}")
        
        if not self.engagement_metrics:
            logger.error("No engagement metrics available")
            return {}
        
        ghost_followers = {}
        active_followers = {}
        
        for username, metrics in self.engagement_metrics.items():
            if metrics['engagement_score'] < threshold:
                ghost_followers[username] = metrics
            else:
                active_followers[username] = metrics
        
        logger.info(f"Identified {len(ghost_followers)} ghost followers out of {len(self.engagement_metrics)} total followers")
        
        return {
            'ghost_followers': ghost_followers,
            'active_followers': active_followers
        }
    
    def categorize_ghost_followers(self):
        """
        Categorize ghost followers into different types:
        - Definite ghosts (no engagement at all)
        - Probable ghosts (very low engagement)
        - Possible ghosts (low engagement but some activity)
        
        Returns:
            Dictionary with categorized ghost followers
        """
        logger.info("Categorizing ghost followers")
        
        if not self.engagement_metrics:
            logger.error("No engagement metrics available")
            return {}
        
        definite_ghosts = {}
        probable_ghosts = {}
        possible_ghosts = {}
        
        for username, metrics in self.engagement_metrics.items():
            # Definite ghosts: No engagement at all
            if metrics['like_count'] == 0 and metrics['comment_count'] == 0 and \
               metrics['story_view_count'] == 0 and metrics['reel_engagement_count'] == 0 and \
               metrics['active_now_count'] == 0:
                definite_ghosts[username] = metrics
            
            # Probable ghosts: Very low engagement score
            elif metrics['engagement_score'] < 0.05:
                probable_ghosts[username] = metrics
            
            # Possible ghosts: Low engagement score
            elif metrics['engagement_score'] < 0.1:
                possible_ghosts[username] = metrics
        
        logger.info(f"Categorized ghost followers: {len(definite_ghosts)} definite, {len(probable_ghosts)} probable, {len(possible_ghosts)} possible")
        
        return {
            'definite_ghosts': definite_ghosts,
            'probable_ghosts': probable_ghosts,
            'possible_ghosts': possible_ghosts
        }
    
    def export_engagement_data(self):
        """
        Export engagement metrics and ghost follower data to CSV files.
        
        Returns:
            Dictionary with file paths
        """
        logger.info("Exporting engagement data to CSV")
        
        if not self.engagement_metrics:
            logger.error("No engagement metrics available")
            return {}
        
        try:
            # Create DataFrame from engagement metrics
            metrics_data = []
            for username, metrics in self.engagement_metrics.items():
                metrics_data.append({
                    'username': username,
                    'like_count': metrics['like_count'],
                    'comment_count': metrics['comment_count'],
                    'story_view_count': metrics['story_view_count'],
                    'reel_engagement_count': metrics['reel_engagement_count'],
                    'active_now_count': metrics['active_now_count'],
                    'posts_seen': metrics['posts_seen'],
                    'stories_seen': metrics['stories_seen'],
                    'reels_seen': metrics['reels_seen'],
                    'activity_checks': metrics['activity_checks'],
                    'last_engagement': metrics['last_engagement'],
                    'engagement_score': metrics['engagement_score']
                })
            
            metrics_df = pd.DataFrame(metrics_data)
            
            # Sort by engagement score (ascending)
            metrics_df = metrics_df.sort_values('engagement_score')
            
            # Export to CSV
            os.makedirs(self.data_dir, exist_ok=True)
            metrics_file = os.path.join(self.data_dir, f"{self.username}_engagement_metrics.csv")
            metrics_df.to_csv(metrics_file, index=False)
            logger.info(f"Engagement metrics exported to {metrics_file}")
            
            # Export ghost followers
            ghost_followers = self.identify_ghost_followers()
            
            ghost_data = []
            for username, metrics in ghost_followers.get('ghost_followers', {}).items():
                ghost_data.append({
                    'username': username,
                    'engagement_score': metrics['engagement_score'],
                    'last_engagement': metrics['last_engagement']
                })
            
            ghost_df = pd.DataFrame(ghost_data)
            ghost_file = os.path.join(self.data_dir, f"{self.username}_ghost_followers.csv")
            ghost_df.to_csv(ghost_file, index=False)
            logger.info(f"Ghost followers exported to {ghost_file}")
            
            # Export categorized ghost followers
            categorized_ghosts = self.categorize_ghost_followers()
            
            # Definite ghosts
            definite_data = []
            for username, metrics in categorized_ghosts.get('definite_ghosts', {}).items():
                definite_data.append({
                    'username': username,
                    'engagement_score': metrics['engagement_score'],
                    'last_engagement': metrics['last_engagement']
                })
            
            definite_df = pd.DataFrame(definite_data)
            definite_file = os.path.join(self.data_dir, f"{self.username}_definite_ghosts.csv")
            definite_df.to_csv(definite_file, index=False)
            logger.info(f"Definite ghost followers exported to {definite_file}")
            
            return {
                'metrics_file': metrics_file,
                'ghost_file': ghost_file,
                'definite_file': definite_file
            }
            
        except Exception as e:
            logger.error(f"Error exporting engagement data: {str(e)}")
            return {} 
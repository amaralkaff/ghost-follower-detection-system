import os
import random
import time
import requests
import json
from datetime import datetime, timedelta

from src.utils.logger import get_default_logger
from src.config.config import PROXY_LIST_PATH, USE_PROXY

# Get logger
logger = get_default_logger()

class ProxyManager:
    """
    Manages proxies with features like:
    - Proxy rotation
    - IP ban detection
    - Proxy validation
    - Automatic proxy refresh
    """
    
    def __init__(self, proxy_list_path=None):
        self.proxy_list_path = proxy_list_path or PROXY_LIST_PATH
        self.proxies = []
        self.banned_proxies = set()
        self.proxy_performance = {}  # Track success/failure rates
        self.last_refresh_time = None
        self.current_proxy = None
        
        # Load proxies on initialization
        self.refresh_proxies()
    
    def refresh_proxies(self):
        """Load proxies from file and validate them."""
        if not USE_PROXY:
            logger.info("Proxy usage is disabled in configuration")
            return
            
        try:
            if os.path.exists(self.proxy_list_path):
                with open(self.proxy_list_path, 'r') as f:
                    raw_proxies = [line.strip() for line in f if line.strip()]
                
                logger.info(f"Loaded {len(raw_proxies)} proxies from {self.proxy_list_path}")
                
                # Reset proxy list but keep performance data
                self.proxies = []
                
                # Validate proxies (optional, can be slow)
                for proxy in raw_proxies:
                    if proxy not in self.banned_proxies:
                        self.proxies.append(proxy)
                
                self.last_refresh_time = datetime.now()
                
                if not self.proxies:
                    logger.warning("No valid proxies found after filtering banned proxies")
            else:
                logger.warning(f"Proxy list file {self.proxy_list_path} not found")
        except Exception as e:
            logger.error(f"Error refreshing proxies: {e}")
    
    def get_proxy(self):
        """Get a random proxy from the list, with preference for better performing ones."""
        if not USE_PROXY or not self.proxies:
            return None
            
        # Check if we need to refresh the proxy list (every 30 minutes)
        if self.last_refresh_time and (datetime.now() - self.last_refresh_time) > timedelta(minutes=30):
            logger.info("Refreshing proxy list (30-minute interval)")
            self.refresh_proxies()
        
        # If we have performance data, prefer better performing proxies
        if self.proxy_performance and random.random() < 0.8:  # 80% chance to use performance data
            # Sort proxies by success rate
            good_proxies = [p for p, stats in self.proxy_performance.items() 
                           if p in self.proxies and stats['success_rate'] > 0.7]
            
            if good_proxies:
                self.current_proxy = random.choice(good_proxies)
                return self.current_proxy
        
        # Otherwise, choose randomly
        if self.proxies:
            self.current_proxy = random.choice(self.proxies)
            return self.current_proxy
        
        return None
    
    def mark_proxy_success(self, proxy=None):
        """Mark a proxy as successful."""
        proxy = proxy or self.current_proxy
        if not proxy:
            return
            
        if proxy not in self.proxy_performance:
            self.proxy_performance[proxy] = {
                'success': 0,
                'failure': 0,
                'success_rate': 0
            }
            
        self.proxy_performance[proxy]['success'] += 1
        total = (self.proxy_performance[proxy]['success'] + 
                self.proxy_performance[proxy]['failure'])
        
        self.proxy_performance[proxy]['success_rate'] = (
            self.proxy_performance[proxy]['success'] / total
        )
    
    def mark_proxy_failure(self, proxy=None, ban=False):
        """Mark a proxy as failed, optionally banning it."""
        proxy = proxy or self.current_proxy
        if not proxy:
            return
            
        if proxy not in self.proxy_performance:
            self.proxy_performance[proxy] = {
                'success': 0,
                'failure': 0,
                'success_rate': 0
            }
            
        self.proxy_performance[proxy]['failure'] += 1
        total = (self.proxy_performance[proxy]['success'] + 
                self.proxy_performance[proxy]['failure'])
        
        self.proxy_performance[proxy]['success_rate'] = (
            self.proxy_performance[proxy]['success'] / total
        )
        
        # If ban is True or success rate is very low, ban the proxy
        if ban or (total > 5 and self.proxy_performance[proxy]['success_rate'] < 0.3):
            logger.info(f"Banning proxy {proxy} due to poor performance or explicit ban")
            self.ban_proxy(proxy)
    
    def ban_proxy(self, proxy=None):
        """Ban a proxy from future use."""
        proxy = proxy or self.current_proxy
        if not proxy:
            return
            
        self.banned_proxies.add(proxy)
        
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            
        # Save banned proxies to file
        try:
            banned_file = os.path.join(os.path.dirname(self.proxy_list_path), 'banned_proxies.txt')
            with open(banned_file, 'a') as f:
                f.write(f"{proxy}\n")
        except Exception as e:
            logger.error(f"Error saving banned proxy: {e}")
    
    def detect_ip_ban(self, response_text):
        """
        Detect if the current IP is banned based on response content.
        
        Args:
            response_text: The HTML response text to analyze
            
        Returns:
            True if IP appears to be banned, False otherwise
        """
        ban_indicators = [
            "unusual traffic",
            "automated requests",
            "temporarily blocked",
            "suspicious activity",
            "please wait",
            "too many requests",
            "rate limit exceeded",
            "captcha",
            "challenge"
        ]
        
        response_lower = response_text.lower()
        
        for indicator in ban_indicators:
            if indicator in response_lower:
                logger.warning(f"IP ban detected: '{indicator}' found in response")
                
                # Ban the current proxy
                if self.current_proxy:
                    self.ban_proxy(self.current_proxy)
                    
                return True
                
        return False
    
    def validate_proxy(self, proxy):
        """
        Validate a proxy by making a test request.
        
        Args:
            proxy: The proxy to validate
            
        Returns:
            True if proxy works, False otherwise
        """
        test_url = "https://www.google.com"
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        
        try:
            response = requests.get(
                test_url, 
                proxies=proxies, 
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.debug(f"Proxy validation failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.debug(f"Proxy validation failed: {e}")
            return False
    
    def save_proxy_performance(self):
        """Save proxy performance data to file for future use."""
        try:
            performance_file = os.path.join(
                os.path.dirname(self.proxy_list_path), 
                'proxy_performance.json'
            )
            
            with open(performance_file, 'w') as f:
                json.dump(self.proxy_performance, f)
                
            logger.info(f"Proxy performance data saved to {performance_file}")
            
        except Exception as e:
            logger.error(f"Error saving proxy performance data: {e}")
    
    def load_proxy_performance(self):
        """Load proxy performance data from file."""
        performance_file = os.path.join(
            os.path.dirname(self.proxy_list_path), 
            'proxy_performance.json'
        )
        
        if not os.path.exists(performance_file):
            return
            
        try:
            with open(performance_file, 'r') as f:
                self.proxy_performance = json.load(f)
                
            logger.info(f"Loaded proxy performance data for {len(self.proxy_performance)} proxies")
            
        except Exception as e:
            logger.error(f"Error loading proxy performance data: {e}")
    
    def get_proxy_stats(self):
        """Get statistics about proxy usage."""
        return {
            "total_proxies": len(self.proxies),
            "banned_proxies": len(self.banned_proxies),
            "tracked_proxies": len(self.proxy_performance),
            "good_proxies": len([p for p, stats in self.proxy_performance.items() 
                               if stats['success_rate'] > 0.7]),
            "current_proxy": self.current_proxy
        } 
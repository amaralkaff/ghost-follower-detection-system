import os
import sys
import getpass
import pickle
from pathlib import Path
from src.utils.browser import setup_browser, get_user_agent
from src.utils.logger import get_default_logger
from src.scrapers.login import login_to_instagram
from src.utils.credential_manager import CredentialManager
from src.scrapers.follower_scraper import FollowerScraper
from src.data.follower_data import FollowerDataManager
import re
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Get logger
logger = get_default_logger()

def main():
    """Test the follower scraper functionality."""
    logger.info("Testing follower scraper")
    
    # Get target username
    target_username = input("Enter target username to scrape followers (leave blank to use your own account): ")
    if not target_username:
        target_username = None
        logger.info("Using logged-in user's followers")
    else:
        logger.info(f"Using target username: {target_username}")
    
    # Set up credentials
    credential_manager = CredentialManager()
    
    # Try auto setup first
    if credential_manager.auto_setup_from_env():
        logger.info("Using automatically set up credentials from environment")
        master_password = os.getenv("MASTER_PASSWORD")
    else:
        # Check if credentials file exists
        credentials_file = os.path.join("credentials", "encrypted_credentials.json")
        
        if not os.path.exists(credentials_file):
            logger.error("No credentials file found. Please run main.py first to set up credentials.")
            return
        
        # Get master password
        master_password = getpass.getpass("Enter master password to decrypt credentials: ")
        if not credential_manager.setup_encryption(master_password):
            logger.error("Failed to set up encryption with provided master password")
            return
    
    # Get credentials
    credentials = credential_manager.get_credentials()
    if not credentials:
        logger.error("Failed to retrieve credentials")
        return
    
    username = credentials["username"]
    
    # Create cookies directory if it doesn't exist
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / f"{username}_cookies.pkl"
    
    # Set up browser
    browser = setup_browser()
    if not browser:
        logger.error("Failed to set up browser")
        return
    
    try:
        # Try to use cookies first if they exist
        if cookie_file.exists():
            logger.info(f"Found existing cookies for {username}")
            
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
                login_successful = True
            else:
                logger.warning("Cookies loaded but login unsuccessful")
                login_successful = False
        else:
            login_successful = False
        
        # If cookies didn't work or don't exist, try regular login
        if not login_successful:
            logger.info("Attempting regular login...")
            login_successful = login_to_instagram(browser, use_encrypted_credentials=True, master_password=master_password)
            
            if login_successful:
                logger.info("Login successful!")
                
                # Save cookies for future use
                logger.info(f"Saving cookies to {cookie_file}")
                with open(cookie_file, "wb") as f:
                    pickle.dump(browser.get_cookies(), f)
                
                # Verify cookies were saved
                if cookie_file.exists():
                    logger.info("Cookies saved successfully")
        
        if not login_successful:
            logger.error("Login failed")
            return
        
        # Initialize follower scraper
        follower_scraper = FollowerScraper(target_username)
        follower_scraper.browser = browser
        
        # Run the scraper
        followers_data = follower_scraper.run()
        
        if not followers_data:
            logger.warning("No follower data collected")
            return
        
        logger.info(f"Collected {len(followers_data)} followers")
        
        # Initialize data manager
        data_manager = FollowerDataManager()
        
        # Get statistics
        stats = data_manager.get_follower_statistics({
            "target_username": follower_scraper.target_username,
            "collection_timestamp": "2023-01-01T00:00:00",
            "total_followers_collected": len(followers_data),
            "followers": followers_data
        })
        
        # Print statistics
        logger.info("Follower Statistics:")
        logger.info(f"Total followers collected: {stats['total_followers']}")
        logger.info(f"Analyzed profiles: {stats['analyzed_profiles']}")
        logger.info(f"Account types: {stats['account_types']}")
        logger.info(f"Privacy status: {stats['privacy_status']}")
        logger.info(f"Potential bots: {stats['potential_bots']}")
        logger.info(f"High follower accounts: {stats['high_follower_accounts']}")
        logger.info(f"Low engagement potential: {stats['low_engagement_potential']}")
        logger.info(f"Average followers: {stats['avg_followers']:.2f}")
        logger.info(f"Average following: {stats['avg_following']:.2f}")
        logger.info(f"Average posts: {stats['avg_posts']:.2f}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        # Close the browser
        if browser:
            browser.quit()
            logger.info("Browser closed")

def test_extract_user_id():
    """
    Test function to extract user ID from Instagram profile page.
    """
    # Get username
    username = input("Enter Instagram username to test (leave blank for your own account): ")
    if not username:
        # Try auto setup first
        credential_manager = CredentialManager()
        if credential_manager.auto_setup_from_env():
            logger.info("Using automatically set up credentials from environment")
            master_password = os.getenv("MASTER_PASSWORD")
        else:
            # Manual setup
            master_password = getpass.getpass("Enter your master password: ")
            if not credential_manager.setup_encryption(master_password):
                logger.error("Failed to set up encryption")
                return
        
        # Get credentials
        credentials = credential_manager.get_credentials()
        
        if not credentials:
            logger.error("Failed to get credentials")
            return
        
        username = credentials.get("username")
        
        if not username:
            logger.error("Username not found in credentials")
            return
    
    # Create cookies directory if it doesn't exist
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / f"{username}_cookies.pkl"
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--user-agent={get_user_agent()}")
    
    # Initialize browser
    browser = webdriver.Chrome(options=chrome_options)
    
    try:
        # Try to use cookies first if they exist
        if cookie_file.exists():
            logger.info(f"Found existing cookies for {username}")
            
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
            
            logger.info("Cookies loaded, proceeding with test")
        
        # Navigate to profile
        profile_url = f"https://www.instagram.com/{username}/"
        logger.info(f"Navigating to profile: {profile_url}")
        browser.get(profile_url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Save page source for debugging
        with open("debug_page_source.html", "w", encoding="utf-8") as f:
            f.write(browser.page_source)
        
        logger.info("Page source saved to debug_page_source.html")
        
        # Try different methods to extract user ID
        
        # Method 1: Extract from page source using regex
        page_source = browser.page_source
        
        user_id_patterns = [
            r'"user_id":"(\d+)"',
            r'"profilePage_(\d+)"',
            r'"owner":{"id":"(\d+)"',
            r'"id":"(\d+)","username":"{}"'.format(username),
            r'instagram://user\?username={}&amp;userid=(\d+)'.format(username)
        ]
        
        for pattern in user_id_patterns:
            match = re.search(pattern, page_source)
            if match:
                user_id = match.group(1)
                logger.info(f"Method 1: Found user ID using pattern '{pattern}': {user_id}")
                break
        
        # Method 2: Extract from window._sharedData
        try:
            shared_data = browser.execute_script("return window._sharedData;")
            if shared_data:
                logger.info("Found window._sharedData")
                
                # Save for debugging
                with open("debug_shared_data.json", "w") as f:
                    json.dump(shared_data, f, indent=2)
                
                logger.info("Shared data saved to debug_shared_data.json")
                
                # Try to extract user ID
                if (shared_data.get("entry_data") and 
                    shared_data["entry_data"].get("ProfilePage") and 
                    shared_data["entry_data"]["ProfilePage"][0].get("graphql") and 
                    shared_data["entry_data"]["ProfilePage"][0]["graphql"].get("user")):
                    
                    user_id = shared_data["entry_data"]["ProfilePage"][0]["graphql"]["user"].get("id")
                    if user_id:
                        logger.info(f"Method 2: Found user ID from _sharedData: {user_id}")
        except Exception as e:
            logger.warning(f"Method 2 failed: {str(e)}")
        
        # Method 3: Extract from script tags
        try:
            scripts = browser.find_elements(By.TAG_NAME, "script")
            logger.info(f"Found {len(scripts)} script tags")
            
            for i, script in enumerate(scripts):
                try:
                    script_content = script.get_attribute("innerHTML")
                    if script_content and username in script_content:
                        logger.info(f"Found script {i} containing username")
                        
                        # Save script content for debugging
                        with open(f"debug_script_{i}.js", "w", encoding="utf-8") as f:
                            f.write(script_content)
                        
                        # Check for user ID in script content
                        for pattern in user_id_patterns:
                            match = re.search(pattern, script_content)
                            if match:
                                user_id = match.group(1)
                                logger.info(f"Method 3: Found user ID in script {i} using pattern '{pattern}': {user_id}")
                                break
                except Exception as e:
                    logger.debug(f"Error processing script {i}: {str(e)}")
        except Exception as e:
            logger.warning(f"Method 3 failed: {str(e)}")
        
        # Method 4: Extract from additional data
        try:
            additional_data = browser.execute_script("""
                const result = {};
                for (const key in window) {
                    if (key.startsWith('__additionalData')) {
                        result[key] = window[key];
                    }
                }
                return result;
            """)
            
            if additional_data:
                logger.info(f"Found additional data: {list(additional_data.keys())}")
                
                # Save for debugging
                with open("debug_additional_data.json", "w") as f:
                    json.dump(str(additional_data), f, indent=2)
                
                logger.info("Additional data saved to debug_additional_data.json")
        except Exception as e:
            logger.warning(f"Method 4 failed: {str(e)}")
        
        # Method 5: Try to find user ID in any JavaScript object
        try:
            js_objects = browser.execute_script("""
                const result = {};
                for (const key in window) {
                    try {
                        const value = window[key];
                        if (value && typeof value === 'object') {
                            if (value.user_id || 
                                (value.user && value.user.id) || 
                                (value.data && value.data.user && value.data.user.id)) {
                                result[key] = {
                                    user_id: value.user_id || (value.user && value.user.id) || (value.data && value.data.user && value.data.user.id)
                                };
                            }
                        }
                    } catch (e) {
                        // Ignore errors
                    }
                }
                return result;
            """)
            
            if js_objects:
                logger.info(f"Found JavaScript objects with user ID: {list(js_objects.keys())}")
                
                for key, value in js_objects.items():
                    logger.info(f"Object {key} has user ID: {value.get('user_id')}")
                
                # Save for debugging
                with open("debug_js_objects.json", "w") as f:
                    json.dump(str(js_objects), f, indent=2)
                
                logger.info("JavaScript objects saved to debug_js_objects.json")
        except Exception as e:
            logger.warning(f"Method 5 failed: {str(e)}")
        
        # Method 6: Try to extract from meta tags
        try:
            meta_tags = browser.find_elements(By.TAG_NAME, "meta")
            logger.info(f"Found {len(meta_tags)} meta tags")
            
            for meta in meta_tags:
                try:
                    content = meta.get_attribute("content")
                    if content and username in content:
                        logger.info(f"Found meta tag with content containing username: {content}")
                        
                        # Check for user ID in content
                        for pattern in user_id_patterns:
                            match = re.search(pattern, content)
                            if match:
                                user_id = match.group(1)
                                logger.info(f"Method 6: Found user ID in meta tag using pattern '{pattern}': {user_id}")
                                break
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Method 6 failed: {str(e)}")
        
        # Method 7: Try to extract from HTML attributes
        try:
            elements_with_data = browser.find_elements(By.CSS_SELECTOR, "[data-user-id]")
            for element in elements_with_data:
                user_id = element.get_attribute("data-user-id")
                if user_id:
                    logger.info(f"Method 7: Found user ID in data-user-id attribute: {user_id}")
                    break
        except Exception as e:
            logger.warning(f"Method 7 failed: {str(e)}")
        
        # Method 8: Try to extract from HTML comments
        try:
            html = browser.page_source
            comment_pattern = r"<!--.*?user_id[\"']?\s*:\s*[\"']?(\d+)[\"']?.*?-->"
            match = re.search(comment_pattern, html, re.DOTALL)
            if match:
                user_id = match.group(1)
                logger.info(f"Method 8: Found user ID in HTML comment: {user_id}")
        except Exception as e:
            logger.warning(f"Method 8 failed: {str(e)}")
        
        # Method 9: Try to extract from any JSON data in the page
        try:
            json_pattern = r'<script[^>]*type=["\'](application|text)\/json["\'][^>]*>(.*?)<\/script>'
            json_matches = re.finditer(json_pattern, page_source, re.DOTALL)
            
            for i, match in enumerate(json_matches):
                try:
                    json_text = match.group(2)
                    json_data = json.loads(json_text)
                    
                    # Save for debugging
                    with open(f"debug_json_{i}.json", "w") as f:
                        json.dump(json_data, f, indent=2)
                    
                    logger.info(f"JSON data {i} saved to debug_json_{i}.json")
                    
                    # Try to find user ID in the JSON data
                    if isinstance(json_data, dict):
                        def find_user_id(data, path=""):
                            if isinstance(data, dict):
                                for key, value in data.items():
                                    if key in ["user_id", "id"] and isinstance(value, (str, int)) and str(value).isdigit():
                                        logger.info(f"Method 9: Found potential user ID in JSON at {path}.{key}: {value}")
                                    
                                    if isinstance(value, (dict, list)):
                                        find_user_id(value, f"{path}.{key}" if path else key)
                            elif isinstance(data, list):
                                for i, item in enumerate(data):
                                    if isinstance(item, (dict, list)):
                                        find_user_id(item, f"{path}[{i}]")
                        
                        find_user_id(json_data)
                except Exception as e:
                    logger.debug(f"Error processing JSON {i}: {str(e)}")
        except Exception as e:
            logger.warning(f"Method 9 failed: {str(e)}")
        
        # Method 10: Try to extract from localStorage
        try:
            local_storage = browser.execute_script("return Object.keys(window.localStorage);")
            logger.info(f"Found localStorage keys: {local_storage}")
            
            for key in local_storage:
                if "user" in key.lower() or "id" in key.lower():
                    value = browser.execute_script(f"return window.localStorage.getItem('{key}');")
                    logger.info(f"localStorage key {key} has value: {value}")
                    
                    # Try to parse as JSON
                    try:
                        json_value = json.loads(value)
                        if isinstance(json_value, dict) and ("id" in json_value or "user_id" in json_value):
                            user_id = json_value.get("id") or json_value.get("user_id")
                            logger.info(f"Method 10: Found user ID in localStorage key {key}: {user_id}")
                    except:
                        # Try regex
                        for pattern in user_id_patterns:
                            match = re.search(pattern, value)
                            if match:
                                user_id = match.group(1)
                                logger.info(f"Method 10: Found user ID in localStorage key {key} using pattern '{pattern}': {user_id}")
                                break
        except Exception as e:
            logger.warning(f"Method 10 failed: {str(e)}")
        
        # Method 11: Try to extract from sessionStorage
        try:
            session_storage = browser.execute_script("return Object.keys(window.sessionStorage);")
            logger.info(f"Found sessionStorage keys: {session_storage}")
            
            for key in session_storage:
                if "user" in key.lower() or "id" in key.lower():
                    value = browser.execute_script(f"return window.sessionStorage.getItem('{key}');")
                    logger.info(f"sessionStorage key {key} has value: {value}")
                    
                    # Try to parse as JSON
                    try:
                        json_value = json.loads(value)
                        if isinstance(json_value, dict) and ("id" in json_value or "user_id" in json_value):
                            user_id = json_value.get("id") or json_value.get("user_id")
                            logger.info(f"Method 11: Found user ID in sessionStorage key {key}: {user_id}")
                    except:
                        # Try regex
                        for pattern in user_id_patterns:
                            match = re.search(pattern, value)
                            if match:
                                user_id = match.group(1)
                                logger.info(f"Method 11: Found user ID in sessionStorage key {key} using pattern '{pattern}': {user_id}")
                                break
        except Exception as e:
            logger.warning(f"Method 11 failed: {str(e)}")
        
        # Method 12: Try to extract from cookies
        try:
            cookies = browser.get_cookies()
            logger.info(f"Found {len(cookies)} cookies")
            
            for cookie in cookies:
                if "user" in cookie["name"].lower() or "id" in cookie["name"].lower():
                    logger.info(f"Cookie {cookie['name']} has value: {cookie['value']}")
                    
                    # Try regex
                    for pattern in user_id_patterns:
                        match = re.search(pattern, cookie["value"])
                        if match:
                            user_id = match.group(1)
                            logger.info(f"Method 12: Found user ID in cookie {cookie['name']} using pattern '{pattern}': {user_id}")
                            break
                    
                    # Check specifically for ds_user_id cookie
                    if cookie["name"] == "ds_user_id":
                        logger.info(f"Found ds_user_id cookie with value: {cookie['value']}")
                        if cookie["value"].isdigit():
                            logger.info(f"Method 12: Found user ID in ds_user_id cookie: {cookie['value']}")
        except Exception as e:
            logger.warning(f"Method 12 failed: {str(e)}")
        
        logger.info("Test completed. Check the logs for results.")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
    finally:
        # Close browser
        browser.quit()

if __name__ == "__main__":
    # Only run the test_extract_user_id function
    test_extract_user_id() 
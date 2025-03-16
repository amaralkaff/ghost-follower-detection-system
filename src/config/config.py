import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Instagram credentials
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
INSTAGRAM_2FA_ENABLED = os.getenv('INSTAGRAM_2FA_ENABLED', 'True').lower() == 'true'

# Browser settings
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'False').lower() == 'true'
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')

# Proxy settings
USE_PROXY = os.getenv('USE_PROXY', 'False').lower() == 'true'
PROXY_LIST_PATH = os.getenv('PROXY_LIST_PATH', 'proxies.txt')

# Scraping settings
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
DELAY_BETWEEN_REQUESTS_MIN = float(os.getenv('DELAY_BETWEEN_REQUESTS_MIN', '2.0'))
DELAY_BETWEEN_REQUESTS_MAX = float(os.getenv('DELAY_BETWEEN_REQUESTS_MAX', '5.0'))

# Data storage
DATA_DIR = os.getenv('DATA_DIR', 'data')
FOLLOWER_DATA_PATH = os.path.join(DATA_DIR, 'followers')
ENGAGEMENT_DATA_PATH = os.path.join(DATA_DIR, 'engagement')
REPORT_DATA_PATH = os.path.join(DATA_DIR, 'reports')

# Create directories if they don't exist
os.makedirs(FOLLOWER_DATA_PATH, exist_ok=True)
os.makedirs(ENGAGEMENT_DATA_PATH, exist_ok=True)
os.makedirs(REPORT_DATA_PATH, exist_ok=True) 
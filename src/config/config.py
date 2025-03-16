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
USER_AGENT_ROTATION = os.getenv('USER_AGENT_ROTATION', 'True').lower() == 'true'
BROWSER_LANGUAGE = os.getenv('BROWSER_LANGUAGE', 'en-US,en;q=0.9')

# Proxy settings
USE_PROXY = os.getenv('USE_PROXY', 'False').lower() == 'true'
PROXY_LIST_PATH = os.getenv('PROXY_LIST_PATH', 'proxies.txt')
PROXY_VALIDATION = os.getenv('PROXY_VALIDATION', 'True').lower() == 'true'
PROXY_ROTATION_INTERVAL = int(os.getenv('PROXY_ROTATION_INTERVAL', '30'))

# Anti-detection settings
SIMULATE_HUMAN_BEHAVIOR = os.getenv('SIMULATE_HUMAN_BEHAVIOR', 'True').lower() == 'true'
RANDOM_MOUSE_MOVEMENTS = os.getenv('RANDOM_MOUSE_MOVEMENTS', 'True').lower() == 'true'
REALISTIC_TYPING = os.getenv('REALISTIC_TYPING', 'True').lower() == 'true'
RANDOM_SCROLLING = os.getenv('RANDOM_SCROLLING', 'True').lower() == 'true'

# Scraping settings
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
DELAY_BETWEEN_REQUESTS_MIN = float(os.getenv('DELAY_BETWEEN_REQUESTS_MIN', '2.0'))
DELAY_BETWEEN_REQUESTS_MAX = float(os.getenv('DELAY_BETWEEN_REQUESTS_MAX', '5.0'))
MAX_REQUESTS_PER_SESSION = int(os.getenv('MAX_REQUESTS_PER_SESSION', '100'))
SESSION_DURATION_MAX = int(os.getenv('SESSION_DURATION_MAX', '3600'))

# Error handling
EXPONENTIAL_BACKOFF = os.getenv('EXPONENTIAL_BACKOFF', 'True').lower() == 'true'
SAVE_ERROR_SCREENSHOTS = os.getenv('SAVE_ERROR_SCREENSHOTS', 'True').lower() == 'true'
ERROR_SCREENSHOT_DIR = os.getenv('ERROR_SCREENSHOT_DIR', 'logs/screenshots')

# Data storage
DATA_DIR = os.getenv('DATA_DIR', 'data')
SESSION_DIR = os.getenv('SESSION_DIR', 'data/sessions')
FOLLOWER_DATA_PATH = os.path.join(DATA_DIR, 'followers')
ENGAGEMENT_DATA_PATH = os.path.join(DATA_DIR, 'engagement')
REPORT_DATA_PATH = os.path.join(DATA_DIR, 'reports')

# Create directories if they don't exist
os.makedirs(FOLLOWER_DATA_PATH, exist_ok=True)
os.makedirs(ENGAGEMENT_DATA_PATH, exist_ok=True)
os.makedirs(REPORT_DATA_PATH, exist_ok=True)
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(ERROR_SCREENSHOT_DIR, exist_ok=True) 
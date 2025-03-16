import os
import base64
import json
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

from src.utils.logger import get_default_logger

# Get logger
logger = get_default_logger()

# Constants
CREDENTIALS_DIR = "credentials"
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "encrypted_credentials.json")
SALT_FILE = os.path.join(CREDENTIALS_DIR, "salt.bin")

class CredentialManager:
    """
    Manages secure storage and retrieval of Instagram credentials.
    Uses encryption to store credentials securely on disk.
    """
    
    def __init__(self):
        """Initialize the credential manager."""
        # Create credentials directory if it doesn't exist
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        
        # Load environment variables
        load_dotenv()
        
        # Initialize encryption key
        self.key = None
    
    def _generate_key(self, password, salt=None):
        """
        Generate an encryption key from a password and salt.
        
        Args:
            password: The password to derive the key from
            salt: Optional salt bytes, will be generated if not provided
            
        Returns:
            tuple: (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def _save_salt(self, salt):
        """Save salt to file."""
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
    
    def _load_salt(self):
        """Load salt from file."""
        if not os.path.exists(SALT_FILE):
            return None
        
        with open(SALT_FILE, "rb") as f:
            return f.read()
    
    def setup_encryption(self, master_password=None):
        """
        Set up encryption with a master password.
        
        Args:
            master_password: Optional master password, will prompt if not provided
            
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            # Get master password if not provided
            if master_password is None:
                master_password = getpass.getpass("Enter master password for credential encryption: ")
            
            # Generate or load salt
            salt = self._load_salt()
            if salt is None:
                _, salt = self._generate_key(master_password)
                self._save_salt(salt)
            
            # Generate key
            key, _ = self._generate_key(master_password, salt)
            self.key = key
            
            return True
        except Exception as e:
            logger.error(f"Error setting up encryption: {str(e)}")
            return False
    
    def encrypt_credentials(self, username, password, two_factor_enabled=False):
        """
        Encrypt and save Instagram credentials.
        
        Args:
            username: Instagram username
            password: Instagram password
            two_factor_enabled: Whether 2FA is enabled
            
        Returns:
            bool: True if credentials saved successfully, False otherwise
        """
        if self.key is None:
            logger.error("Encryption key not set up. Call setup_encryption() first.")
            return False
        
        try:
            # Create credentials dictionary
            credentials = {
                "username": username,
                "password": password,
                "two_factor_enabled": two_factor_enabled
            }
            
            # Convert to JSON string
            credentials_json = json.dumps(credentials)
            
            # Encrypt
            fernet = Fernet(self.key)
            encrypted_data = fernet.encrypt(credentials_json.encode())
            
            # Save to file
            with open(CREDENTIALS_FILE, "wb") as f:
                f.write(encrypted_data)
            
            logger.info(f"Credentials for {username} encrypted and saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error encrypting credentials: {str(e)}")
            return False
    
    def decrypt_credentials(self):
        """
        Decrypt and return saved Instagram credentials.
        
        Returns:
            dict: Dictionary containing username, password, and two_factor_enabled
                  or None if decryption fails
        """
        if self.key is None:
            logger.error("Encryption key not set up. Call setup_encryption() first.")
            return None
        
        if not os.path.exists(CREDENTIALS_FILE):
            logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
            return None
        
        try:
            # Read encrypted data
            with open(CREDENTIALS_FILE, "rb") as f:
                encrypted_data = f.read()
            
            # Decrypt
            fernet = Fernet(self.key)
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Parse JSON
            credentials = json.loads(decrypted_data.decode())
            
            logger.info(f"Credentials for {credentials['username']} decrypted successfully")
            return credentials
        except Exception as e:
            logger.error(f"Error decrypting credentials: {str(e)}")
            return None
    
    def store_credentials_from_env(self):
        """
        Store credentials from environment variables.
        
        Returns:
            bool: True if credentials stored successfully, False otherwise
        """
        # Get credentials from environment variables
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        two_factor_enabled = os.getenv("INSTAGRAM_2FA_ENABLED", "True").lower() == "true"
        
        if not username or not password:
            logger.error("Instagram credentials not found in environment variables")
            return False
        
        # Encrypt and save credentials
        return self.encrypt_credentials(username, password, two_factor_enabled)
    
    def get_credentials(self):
        """
        Get Instagram credentials, either from encrypted storage or environment variables.
        
        Returns:
            dict: Dictionary containing username, password, and two_factor_enabled
                  or None if credentials not available
        """
        # Try to get credentials from encrypted storage
        credentials = self.decrypt_credentials()
        if credentials:
            return credentials
        
        # Fall back to environment variables
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        two_factor_enabled = os.getenv("INSTAGRAM_2FA_ENABLED", "True").lower() == "true"
        
        if username and password:
            return {
                "username": username,
                "password": password,
                "two_factor_enabled": two_factor_enabled
            }
        
        return None 
import os
import time
from datetime import datetime
from selenium.common.exceptions import WebDriverException

from src.utils.logger import get_default_logger
from src.config.config import ERROR_SCREENSHOT_DIR, SAVE_ERROR_SCREENSHOTS

# Get logger
logger = get_default_logger()

class ScreenshotManager:
    """
    Manages screenshots for debugging and error reporting.
    """
    
    def __init__(self, browser=None):
        """
        Initialize the screenshot manager.
        
        Args:
            browser: The browser instance (optional)
        """
        self.browser = browser
        self.screenshot_dir = ERROR_SCREENSHOT_DIR
        
        # Create screenshot directory if it doesn't exist
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def set_browser(self, browser):
        """
        Set the browser instance.
        
        Args:
            browser: The browser instance
        """
        self.browser = browser
    
    def take_screenshot(self, name=None, error_context=None):
        """
        Take a screenshot of the current browser state.
        
        Args:
            name: Custom name for the screenshot (optional)
            error_context: Error context information (optional)
            
        Returns:
            Path to the saved screenshot or None if failed
        """
        if not SAVE_ERROR_SCREENSHOTS or not self.browser:
            return None
            
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = name or f"screenshot_{timestamp}"
            
            # Add error context to filename if provided
            if error_context:
                error_type = error_context.get('error_type', 'error')
                name = f"{name}_{error_type}"
            
            # Ensure filename is valid
            name = "".join(c for c in name if c.isalnum() or c in ['_', '-'])
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # Take screenshot
            self.browser.save_screenshot(filepath)
            
            logger.info(f"Screenshot saved to {filepath}")
            
            # Log additional error context
            if error_context:
                logger.info(f"Screenshot context: {error_context}")
                
                # Save error context to a text file
                context_file = os.path.join(self.screenshot_dir, f"{name}_{timestamp}.txt")
                with open(context_file, 'w') as f:
                    for key, value in error_context.items():
                        f.write(f"{key}: {value}\n")
            
            return filepath
            
        except WebDriverException as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return None
    
    def take_error_screenshot(self, error, page_url=None, element_id=None):
        """
        Take a screenshot specifically for an error situation.
        
        Args:
            error: The exception that occurred
            page_url: The URL of the page (optional)
            element_id: ID of the element that caused the error (optional)
            
        Returns:
            Path to the saved screenshot or None if failed
        """
        if not SAVE_ERROR_SCREENSHOTS or not self.browser:
            return None
            
        try:
            # Get current URL if not provided
            if not page_url:
                try:
                    page_url = self.browser.current_url
                except:
                    page_url = "unknown"
            
            # Create error context
            error_context = {
                'error_type': type(error).__name__,
                'error_message': str(error),
                'page_url': page_url,
                'timestamp': datetime.now().isoformat()
            }
            
            if element_id:
                error_context['element_id'] = element_id
            
            # Take screenshot with error context
            return self.take_screenshot(
                name=f"error_{type(error).__name__}",
                error_context=error_context
            )
            
        except Exception as e:
            logger.error(f"Failed to take error screenshot: {str(e)}")
            return None
    
    def take_periodic_screenshots(self, interval=300, duration=3600):
        """
        Take screenshots periodically for a specified duration.
        Useful for debugging long-running processes.
        
        Args:
            interval: Time between screenshots in seconds
            duration: Total duration to take screenshots in seconds
            
        Returns:
            List of paths to saved screenshots
        """
        if not self.browser:
            return []
            
        screenshot_paths = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                path = self.take_screenshot(name="periodic")
                if path:
                    screenshot_paths.append(path)
                
                # Sleep until next interval
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Periodic screenshots interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error during periodic screenshot: {str(e)}")
                time.sleep(interval)
        
        return screenshot_paths

# Create a global instance for easy access
screenshot_manager = ScreenshotManager() 
import time
import random
import traceback
import functools
from datetime import datetime

from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    ElementNotInteractableException
)

from src.utils.logger import get_default_logger
from src.config.config import MAX_RETRIES

# Get logger
logger = get_default_logger()

class ScraperException(Exception):
    """Base exception class for scraper errors."""
    pass

class LoginFailedException(ScraperException):
    """Exception raised when login fails."""
    pass

class BannedIPException(ScraperException):
    """Exception raised when IP is banned."""
    pass

class CaptchaDetectedException(ScraperException):
    """Exception raised when CAPTCHA is detected."""
    pass

class RateLimitedException(ScraperException):
    """Exception raised when rate limit is exceeded."""
    pass

class DataExtractionException(ScraperException):
    """Exception raised when data extraction fails."""
    pass

def retry_on_exception(max_retries=None, exceptions=None, backoff_factor=2, 
                      jitter=True, on_retry=None):
    """
    Decorator for retrying a function on specified exceptions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries (default: from config)
        exceptions: Tuple of exceptions to catch (default: WebDriverException)
        backoff_factor: Base factor for exponential backoff (default: 2)
        jitter: Whether to add random jitter to backoff time (default: True)
        on_retry: Function to call before retry (e.g., to restart browser)
        
    Returns:
        Decorated function
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
        
    if exceptions is None:
        exceptions = (WebDriverException,)
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    retries += 1
                    
                    if retries > max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    # Log the exception
                    logger.warning(f"Retry {retries}/{max_retries} due to: {str(e)}")
                    
                    # Calculate backoff time
                    backoff_time = backoff_factor ** retries
                    
                    # Add jitter if enabled
                    if jitter:
                        backoff_time += random.uniform(0, 1)
                    
                    # Call on_retry function if provided
                    if on_retry:
                        try:
                            on_retry(*args, **kwargs)
                        except Exception as retry_error:
                            logger.error(f"Error in on_retry function: {str(retry_error)}")
                    
                    logger.info(f"Waiting {backoff_time:.2f} seconds before retry...")
                    time.sleep(backoff_time)
            
            # This should not be reached due to the raise in the loop
            raise last_exception
        
        return wrapper
    
    return decorator

def handle_selenium_exceptions(func):
    """
    Decorator to handle common Selenium exceptions with appropriate actions.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TimeoutException as e:
            logger.warning(f"Timeout occurred: {str(e)}")
            raise ScraperException(f"Operation timed out: {str(e)}")
        except NoSuchElementException as e:
            logger.warning(f"Element not found: {str(e)}")
            raise ScraperException(f"Element not found: {str(e)}")
        except ElementClickInterceptedException as e:
            logger.warning(f"Click intercepted: {str(e)}")
            raise ScraperException(f"Element click was intercepted: {str(e)}")
        except StaleElementReferenceException as e:
            logger.warning(f"Stale element: {str(e)}")
            raise ScraperException(f"Element is stale: {str(e)}")
        except ElementNotInteractableException as e:
            logger.warning(f"Element not interactable: {str(e)}")
            raise ScraperException(f"Element not interactable: {str(e)}")
        except WebDriverException as e:
            if "captcha" in str(e).lower():
                logger.error(f"CAPTCHA detected: {str(e)}")
                raise CaptchaDetectedException(f"CAPTCHA detected: {str(e)}")
            elif any(term in str(e).lower() for term in ["rate limit", "too many requests"]):
                logger.error(f"Rate limited: {str(e)}")
                raise RateLimitedException(f"Rate limited: {str(e)}")
            elif any(term in str(e).lower() for term in ["banned", "blocked", "unusual traffic"]):
                logger.error(f"IP possibly banned: {str(e)}")
                raise BannedIPException(f"IP possibly banned: {str(e)}")
            else:
                logger.error(f"WebDriver error: {str(e)}")
                raise ScraperException(f"WebDriver error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            logger.debug(traceback.format_exc())
            raise ScraperException(f"Unexpected error: {str(e)}")
    
    return wrapper

def log_execution_time(func):
    """
    Decorator to log the execution time of a function.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        logger.debug(f"Starting {func.__name__} at {start_time}")
        
        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.debug(f"Completed {func.__name__} in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.debug(f"Failed {func.__name__} after {execution_time:.2f} seconds: {str(e)}")
            raise
    
    return wrapper

def create_error_report(exception, context=None):
    """
    Create a detailed error report for debugging.
    
    Args:
        exception: The exception that occurred
        context: Additional context information (dict)
        
    Returns:
        Error report as a dictionary
    """
    error_report = {
        "timestamp": datetime.now().isoformat(),
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "traceback": traceback.format_exc()
    }
    
    if context:
        error_report["context"] = context
        
    # Log the error report
    logger.error(f"Error report: {error_report}")
    
    return error_report 
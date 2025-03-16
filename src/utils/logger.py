import os
import logging
from datetime import datetime

def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up and return a logger with the specified name and level.
    
    Args:
        name: Name of the logger
        log_file: Path to the log file (if None, logs to console only)
        level: Logging level (default: INFO)
        
    Returns:
        A configured logger instance
    """
    # Create logs directory if it doesn't exist
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_default_logger():
    """
    Get a default logger that logs to both console and a file.
    
    Returns:
        A configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log file name with current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(logs_dir, f'instagram_scraper_{current_date}.log')
    
    return setup_logger('instagram_scraper', log_file) 
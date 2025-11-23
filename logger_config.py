"""
Logging configuration for Distributed Deadlock Simulation
"""
import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configure logger
LOG_FILE = os.path.join(LOG_DIR, f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

def setup_logger(name, log_file=LOG_FILE, level=logging.INFO):
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# Create main logger
logger = setup_logger(__name__)

def log_info(msg):
    """Log info message"""
    logger.info(msg)

def log_warning(msg):
    """Log warning message"""
    logger.warning(msg)

def log_error(msg):
    """Log error message"""
    logger.error(msg)

def log_debug(msg):
    """Log debug message"""
    logger.debug(msg)

"""
Centralized logging configuration for McLemore Auction Tools
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(app=None):
    """
    Set up logging configuration with rotating file handler
    If app is provided, also set up Flask app logging
    """
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Rotating file handler
    file_handler = RotatingFileHandler(
        filename=log_dir / 'mclemore.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Configure Flask app logging if app is provided
    if app:
        app.logger.handlers = []  # Remove default handlers
        app.logger.propagate = True  # Use root logger handlers
        
        if not app.debug:
            app.logger.setLevel(logging.INFO)
        else:
            app.logger.setLevel(logging.DEBUG)
    
    return root_logger

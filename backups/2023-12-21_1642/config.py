import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Data directory
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

# Flask config
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')  # Fallback for development
    
    # API Keys
    AM_API_KEY = os.getenv('AM_API_KEY')
    LOB_API_KEY = os.getenv('LOB_API_KEY')
    
    # Email settings
    EMAIL_FROM = os.getenv('EMAIL_FROM')
    EMAIL_TO = os.getenv('EMAIL_TO')
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    @staticmethod
    def init_app(app):
        # Create data directory
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Validate required environment variables
        required_vars = ['AM_API_KEY', 'LOB_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

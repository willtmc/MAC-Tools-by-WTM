"""Application configuration."""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
BASE_AUCTION_URL = os.getenv('BASE_AUCTION_URL', 'https://www.mclemoreauction.com')
BASE_TOOLS_URL = os.getenv('BASE_TOOLS_URL', 'https://tools.mclemoreauction.com')
BASE_API_URL = os.getenv('BASE_API_URL', 'https://www.mclemoreauction.com/uapi')

class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')  # Fallback for development
    
    # API Keys
    AM_API_KEY = os.getenv('AM_API_KEY')
    LOB_API_KEY = os.getenv('LOB_API_KEY')
    
    # Required environment variables
    @staticmethod
    def validate_config() -> List[str]:
        """
        Validate that all required environment variables are set
        
        Returns:
            List[str]: List of missing environment variables
        """
        required_vars = [
            'AM_API_KEY',
            'LOB_API_KEY',
            'SECRET_KEY'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        return missing_vars

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SECRET_KEY = 'test_key'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

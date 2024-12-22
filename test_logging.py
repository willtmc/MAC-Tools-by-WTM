"""
Test script to verify the logging configuration
"""
import logging
from logging_config import setup_logging
from auction_api import AuctionMethodAPI
from flask import Flask

def test_logging():
    # Create a test Flask app
    app = Flask(__name__)
    
    # Set up logging
    logger = setup_logging(app)
    
    # Get module logger
    test_logger = logging.getLogger(__name__)
    
    # Test different log levels
    test_logger.info("Testing INFO level logging")
    test_logger.warning("Testing WARNING level logging")
    test_logger.error("Testing ERROR level logging")
    
    # Test logging with string formatting
    test_data = {"key": "value"}
    test_logger.info("Testing structured data logging: %s", test_data)
    
    # Test API logging
    try:
        api = AuctionMethodAPI()
        api.get_auction_details("test-auction")
    except Exception as e:
        test_logger.error("Expected error testing API: %s", str(e))
    
    print("\nLog test completed. Check logs/mclemore.log for the output.")

if __name__ == "__main__":
    test_logging()

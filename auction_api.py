import os
import requests
import logging
import json
from typing import Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
from config import BASE_API_URL

# Get module logger
logger = logging.getLogger(__name__)

class AuctionAPIError(Exception):
    """Base exception for auction API errors"""
    pass

class AuctionNotFoundError(AuctionAPIError):
    """Raised when auction is not found"""
    pass

class AuctionMethodAPI:
    def __init__(self):
        self.api_key = os.getenv('AM_API_KEY')
        if not self.api_key:
            logger.error("AM_API_KEY environment variable not set")
            raise ValueError("AM_API_KEY environment variable not set")
        
        self.base_url = BASE_API_URL
        self.headers = {
            'X-ApiKey': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        logger.info("Initialized AuctionMethodAPI with URL: %s", self.base_url)

    def get_auction_details(self, auction_code: str) -> Dict:
        """
        Fetch auction details from McLemore Auction API
        
        Args:
            auction_code: The auction code to fetch details for
            
        Returns:
            Dict containing formatted auction details
        """
        if not auction_code:
            raise ValueError("Auction code cannot be empty")
            
        try:
            # Direct URL to auction endpoint
            url = f"https://www.mclemoreauction.com/uapi/auction/{auction_code}"
            logger.info("Fetching auction details from: %s", url)
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
            except Timeout:
                logger.error("Request timed out for auction %s", auction_code)
                raise
            except ConnectionError as e:
                logger.error("Connection error for auction %s: %s", auction_code, str(e))
                raise
            except HTTPError as e:
                if response.status_code == 404:
                    raise AuctionNotFoundError(f"Auction {auction_code} not found")
                logger.error("HTTP error %d for auction %s: %s", 
                           response.status_code, auction_code, response.text)
                raise
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON response for auction %s: %s", auction_code, str(e))
                raise AuctionAPIError("Invalid API response format") from e
            
            # Extract auction data from the response
            auction_data = data
            if not auction_data:
                raise AuctionNotFoundError(f"No data found for auction {auction_code}")
            
            # Convert timestamp to date string if present
            starts = auction_data.get('starts')
            try:
                date_str = datetime.fromtimestamp(int(starts)).strftime('%Y-%m-%d') if starts else ''
            except (ValueError, TypeError) as e:
                logger.warning("Invalid timestamp for auction %s: %s", auction_code, str(e))
                date_str = ''
            
            # Clean description using BeautifulSoup
            description = self._clean_description(auction_data.get('description', ''))
            
            return {
                'title': auction_data.get('title', ''),
                'description': description,
                'date': date_str,
                'time': auction_data.get('timezone', ''),
                'location': f"{auction_data.get('address', '')}, {auction_data.get('city', '')}, {auction_data.get('state', '')} {auction_data.get('zip', '')}",
                'auction_code': auction_code
            }
            
        except (RequestException, AuctionAPIError) as e:
            # Log and re-raise all request-related exceptions
            logger.error("Error fetching auction %s: %s", auction_code, str(e))
            raise

    def _clean_description(self, description: str) -> str:
        """
        Clean HTML from description and format text
        
        Args:
            description: HTML description to clean
            
        Returns:
            Cleaned and formatted text
            
        Raises:
            None: Returns empty string for invalid input
        """
        if not description:
            return ''
            
        try:
            soup = BeautifulSoup(description, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text and clean whitespace
            text = soup.get_text(separator=' ')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return ' '.join(lines)
            
        except Exception as e:
            # Log but don't raise - return empty string for any parsing errors
            logger.warning("Error cleaning description: %s", str(e))
            return ''

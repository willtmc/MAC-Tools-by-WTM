import os
import requests
import logging
import json
from typing import Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout

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
        
        self.base_url = "https://www.mclemoreauction.com/uapi"
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
            
        Raises:
            AuctionNotFoundError: If the auction is not found
            HTTPError: If the API returns an error status code
            ConnectionError: If there's a network connection error
            Timeout: If the API request times out
            json.JSONDecodeError: If the API response is not valid JSON
            AuctionAPIError: For other API-related errors
        """
        if not auction_code:
            raise ValueError("Auction code cannot be empty")
            
        try:
            url = f"{self.base_url}/auction/{auction_code}"
            logger.info("Fetching auction details from: %s", url)
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()  # Raises HTTPError for bad status codes
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
            
            if data.get('message') != 'success':
                error_msg = f"API returned error: {data.get('message')}"
                logger.error(error_msg)
                raise AuctionAPIError(error_msg)
            
            # Extract auction data from the response
            auction_data = data.get('auction', {})
            if not auction_data:
                raise AuctionNotFoundError(f"No data found for auction {auction_code}")
            
            # Convert timestamp to date string
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

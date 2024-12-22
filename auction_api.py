import os
import requests
import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime

# Get module logger
logger = logging.getLogger(__name__)

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
        Returns formatted auction details or raises exception
        """
        try:
            url = f"{self.base_url}/auction/{auction_code}"
            logger.info("Fetching auction details from: %s", url)
            
            response = requests.get(url, headers=self.headers)
            logger.info("Response status code: %s", response.status_code)
            
            if response.status_code != 200:
                logger.error("API error response: %s", response.text)
                raise Exception(f"API returned status code {response.status_code}: {response.text}")
                
            data = response.json()
            logger.info("Successfully fetched auction details for %s", auction_code)
            
            if data.get('message') != 'success':
                logger.error("API returned error message: %s", data.get('message'))
                raise Exception(f"API returned error: {data.get('message')}")
            
            # Extract auction data from the response
            auction_data = data.get('auction', {})
            
            # Convert timestamp to date string
            starts = auction_data.get('starts')
            date_str = datetime.fromtimestamp(int(starts)).strftime('%Y-%m-%d') if starts else ''
            
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
            
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching auction %s: %s", auction_code, str(e))
            raise

    def _clean_description(self, description: str) -> str:
        """Clean HTML from description and format text"""
        if not description:
            return ''
            
        soup = BeautifulSoup(description, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text and clean whitespace
        text = soup.get_text(separator=' ')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = ' '.join(lines)
        
        return text

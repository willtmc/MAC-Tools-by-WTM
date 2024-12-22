import os
import requests
import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

class AuctionMethodAPI:
    def __init__(self):
        self.api_key = os.getenv('AM_API_KEY')
        if not self.api_key:
            raise ValueError("AM_API_KEY environment variable not set")
        
        self.base_url = "https://www.mclemoreauction.com/uapi"
        self.headers = {
            'X-ApiKey': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        logger.info(f"Initialized AuctionMethodAPI with URL: {self.base_url}")

    def get_auction_details(self, auction_code: str) -> Dict:
        """
        Fetch auction details from McLemore Auction API
        Returns formatted auction details or raises exception
        """
        try:
            url = f"{self.base_url}/auction/{auction_code}"
            logger.info(f"Fetching auction details from: {url}")
            
            response = requests.get(url, headers=self.headers, verify=False)
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API error response: {response.text}")
                raise Exception(f"API returned status code {response.status_code}: {response.text}")
                
            data = response.json()
            logger.info(f"Successfully fetched auction details for {auction_code}")
            
            if data.get('message') != 'success':
                logger.error(f"API returned error message: {data.get('message')}")
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
            logger.error(f"Error fetching auction {auction_code}: {str(e)}")
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

import os
import lob
import pandas as pd
import logging
from typing import Dict, List, Optional
from utils.csv_utils import read_csv_flexibly, CSVReadError

logger = logging.getLogger(__name__)

class LetterGenerator:
    """Generate letters from processed neighbor data"""
    
    def __init__(self):
        self.lob_api_key = os.getenv('LOB_API_KEY')
        if not self.lob_api_key:
            raise ValueError("LOB_API_KEY environment variable not set")
            
        lob.api_key = self.lob_api_key

    def create_campaign(self, auction_code: str) -> str:
        """Create a Lob campaign for neighbor letters"""
        try:
            campaign = lob.Campaign.create(
                description=f"Neighbor Letters - Auction {auction_code}",
                name=f"Neighbor Letters {auction_code}",
                schedule_type="immediate"
            )
            logger.info(f"Created campaign {campaign.id} for auction {auction_code}")
            return campaign.id
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            raise

    def load_data(self, auction_code: str) -> pd.DataFrame:
        """
        Load processed neighbor data from CSV
        
        Returns:
            pd.DataFrame: Loaded neighbor data
            
        Raises:
            FileNotFoundError: If data file does not exist
            CSVReadError: If data file cannot be read
        """
        data_file = f'data/processed-neighbors-{auction_code}.csv'
        
        if not os.path.exists(data_file):
            logger.error(f"Data file not found: {data_file}")
            raise FileNotFoundError(f"No processed data found for auction {auction_code}")
            
        try:
            df = read_csv_flexibly(data_file)
            logger.info(f"Loaded {len(df)} records from {data_file}")
            return df
            
        except CSVReadError as e:
            logger.error(f"Error reading data file: {str(e)}")
            raise
        except pd.errors.EmptyDataError:
            logger.error("Data file is empty")
            raise CSVReadError("No data found in processed file")

    def create_creative(self, campaign_id: str, auction_code: str, letter_html: str) -> str:
        """Create a Lob creative for the campaign"""
        try:
            creative = lob.Creative.create(
                campaign_id=campaign_id,
                description=f"Neighbor Letter Template - Auction {auction_code}",
                from_address={
                    "name": "McLemore Auction Company",
                    "address_line1": "P.O. Box 58",
                    "address_city": "Columbia",
                    "address_state": "TN",
                    "address_zip": "38402"
                },
                file=letter_html,
                details={
                    "mail_type": "usps_first_class",
                    "size": "8.5x11",
                }
            )
            logger.info(f"Created creative {creative.id} for campaign {campaign_id}")
            return creative.id
        except Exception as e:
            logger.error(f"Error creating creative: {str(e)}")
            raise

    def create_upload(self, campaign_id: str, auction_code: str) -> str:
        """Create a Lob upload for the campaign using processed CSV"""
        try:
            df = self.load_data(auction_code)
            
            # Format addresses for Lob
            addresses = []
            for _, row in df.iterrows():
                address = {
                    "name": row['Name'],
                    "address_line1": row['Address'],
                    "address_city": row['City'],
                    "address_state": row['State'],
                    "address_zip": row['Zip']
                }
                addresses.append(address)

            # Create upload
            upload = lob.Upload.create(
                campaign_id=campaign_id,
                addresses=addresses
            )
            
            logger.info(f"Created upload {upload.id} for campaign {campaign_id}")
            return upload.id
            
        except Exception as e:
            logger.error(f"Error creating upload: {str(e)}")
            raise

    def send_campaign(self, campaign_id: str) -> None:
        """Send the Lob campaign"""
        try:
            campaign = lob.Campaign.send(campaign_id)
            logger.info(f"Sent campaign {campaign_id}")
        except Exception as e:
            logger.error(f"Error sending campaign: {str(e)}")
            raise

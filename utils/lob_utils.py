"""
Utility module for handling Lob API interactions.
Provides a clean interface for creating and managing direct mail campaigns.
"""

import os
import logging
from typing import Dict, List, Optional, Union, Any
import lob
import pandas as pd
from dotenv import load_dotenv
from .csv_utils import read_csv_flexibly, CSVReadError
from dataclasses import dataclass

# Load environment variables
load_dotenv()

# Get module logger
logger = logging.getLogger(__name__)

class LobError(Exception):
    """Base exception for Lob API errors"""
    pass

class LobAPIError(LobError):
    """Raised when Lob API returns an error"""
    pass

class LobConfigError(LobError):
    """Raised when there's a configuration error"""
    pass

class LobDataError(LobError):
    """Raised when there's an error with the input data"""
    pass

@dataclass
class Address:
    """Address data class for Lob API."""
    name: str
    address_line1: str
    address_city: str
    address_state: str
    address_zip: str

class LobClient:
    """Client for interacting with Lob API for direct mail campaigns"""
    
    DEFAULT_FROM_ADDRESS = {
        "name": "McLemore Auction Company",
        "address_line1": "P.O. Box 58",
        "address_city": "Columbia",
        "address_state": "TN",
        "address_zip": "38402"
    }
    
    def __init__(self):
        """Initialize Lob client with API key from environment"""
        self.api_key = os.getenv('LOB_API_KEY')
        if not self.api_key:
            logger.error("LOB_API_KEY environment variable not set")
            raise LobConfigError("LOB_API_KEY environment variable not set")
            
        try:
            self.lob = lob.Client(api_key=self.api_key)
            logger.info("Successfully initialized Lob client")
        except Exception as e:
            logger.error(f"Error initializing Lob client: {str(e)}")
            raise LobConfigError(f"Error initializing Lob client: {str(e)}")
    
    def create_campaign(self, 
                       name: str, 
                       description: str = None,
                       schedule_type: str = "immediate") -> Dict:
        """
        Create a new mail campaign
        
        Args:
            name: Campaign name
            description: Optional campaign description
            schedule_type: When to send the campaign (immediate or scheduled)
            
        Returns:
            Dict containing campaign details
            
        Raises:
            LobAPIError: If campaign creation fails
        """
        try:
            campaign = self.lob.campaigns.create(
                name=name,
                description=description or f"Campaign: {name}",
                schedule_type=schedule_type
            )
            logger.info(f"Created campaign: {name}")
            return campaign
            
        except lob.error.APIError as e:
            logger.error(f"Error creating campaign {name}: {str(e)}")
            raise LobAPIError(f"Error creating campaign: {str(e)}")
    
    def create_creative(self, 
                       campaign_id: str,
                       content: str,
                       description: str = None,
                       from_address: Dict = None,
                       mail_type: str = "usps_first_class",
                       size: str = "8.5x11") -> Dict:
        """
        Create a new creative for a campaign
        
        Args:
            campaign_id: ID of the campaign
            content: HTML content for the creative
            description: Optional creative description
            from_address: Optional sender address dictionary
            mail_type: Type of mail service
            size: Paper size
            
        Returns:
            Dict containing creative details
            
        Raises:
            LobAPIError: If creative creation fails
        """
        try:
            creative = self.lob.creatives.create(
                campaign_id=campaign_id,
                file=content,
                description=description,
                from_address=from_address or self.DEFAULT_FROM_ADDRESS,
                details={
                    "mail_type": mail_type,
                    "size": size
                }
            )
            logger.info(f"Created creative for campaign {campaign_id}")
            return creative
            
        except lob.error.APIError as e:
            logger.error(f"Error creating creative for campaign {campaign_id}: {str(e)}")
            raise LobAPIError(f"Error creating creative: {str(e)}")
    
    def load_addresses(self, auction_code: str) -> List[Address]:
        """
        Load processed neighbor data from CSV
        
        Args:
            auction_code: Auction code to load data for
            
        Returns:
            List of address dictionaries
            
        Raises:
            FileNotFoundError: If data file does not exist
            LobDataError: If data file cannot be read or is empty
        """
        data_file = os.path.join('data', auction_code, 'processed_addresses.csv')
        
        if not os.path.exists(data_file):
            logger.error(f"Data file not found: {data_file}")
            raise FileNotFoundError(f"No processed data found for auction {auction_code}")
            
        try:
            df = read_csv_flexibly(data_file)
            if df.empty:
                raise LobDataError("No data found in processed file")
                
            # Format addresses for Lob
            addresses = []
            for _, row in df.iterrows():
                address = Address(
                    name=row['Name'],
                    address_line1=row['Address'],
                    address_city=row['City'],
                    address_state=row['State'],
                    address_zip=row['Zip']
                )
                addresses.append(address)
                
            logger.info(f"Loaded {len(addresses)} addresses for auction {auction_code}")
            return addresses
            
        except CSVReadError as e:
            logger.error(f"Error reading data file: {str(e)}")
            raise LobDataError(f"Error reading address data: {str(e)}")
        except pd.errors.EmptyDataError:
            logger.error("Data file is empty")
            raise LobDataError("No data found in processed file")
        except Exception as e:
            logger.error(f"Error loading addresses: {str(e)}")
            raise LobDataError(f"Error loading addresses: {str(e)}")
    
    def create_upload(self, 
                     campaign_id: str,
                     addresses: List[Address]) -> Dict:
        """
        Create a Lob upload for the campaign
        
        Args:
            campaign_id: ID of the campaign
            addresses: List of address dictionaries
            
        Returns:
            Dict containing upload details
            
        Raises:
            LobAPIError: If upload creation fails
            LobDataError: If address data is invalid
        """
        if not addresses:
            raise LobDataError("No addresses provided for upload")
            
        try:
            upload = self.lob.uploads.create(
                campaign_id=campaign_id,
                addresses=[{
                    'name': addr.name,
                    'address_line1': addr.address_line1,
                    'address_city': addr.address_city,
                    'address_state': addr.address_state,
                    'address_zip': addr.address_zip
                } for addr in addresses]
            )
            
            logger.info(f"Created upload for campaign {campaign_id} with {len(addresses)} addresses")
            return upload
            
        except lob.error.APIError as e:
            logger.error(f"Error creating upload for campaign {campaign_id}: {str(e)}")
            raise LobAPIError(f"Error creating upload: {str(e)}")
    
    def send_campaign(self, 
                     campaign_id: str,
                     creative_id: str = None,
                     addresses: List[Address] = None,
                     schedule_date: Optional[str] = None) -> Dict:
        """
        Send a campaign to a list of addresses
        
        Args:
            campaign_id: ID of the campaign
            creative_id: Optional ID of the creative to use
            addresses: Optional list of addresses (if not already uploaded)
            schedule_date: Optional date to schedule the campaign
            
        Returns:
            Dict containing campaign send details
            
        Raises:
            LobAPIError: If sending campaign fails
        """
        try:
            # Upload addresses if provided
            if addresses:
                upload_result = self.create_upload(campaign_id, addresses)
            
            # Send campaign
            campaign = self.lob.campaigns.send(
                id=campaign_id,
                creative_id=creative_id,
                schedule_date=schedule_date
            )
            
            logger.info(f"Successfully sent campaign {campaign_id}")
            return campaign
            
        except LobError as e:
            # Re-raise LobError exceptions
            raise
        except Exception as e:
            logger.error(f"Error sending campaign {campaign_id}: {str(e)}")
            raise LobAPIError(f"Error sending campaign: {str(e)}")
    
    def get_campaign_status(self, campaign_id: str) -> Dict:
        """
        Get the current status of a campaign
        
        Args:
            campaign_id: ID of the campaign
            
        Returns:
            Dict containing campaign status details
            
        Raises:
            LobAPIError: If getting status fails
        """
        try:
            campaign = self.lob.campaigns.retrieve(campaign_id)
            return campaign
            
        except lob.error.APIError as e:
            logger.error(f"Error getting status for campaign {campaign_id}: {str(e)}")
            raise LobAPIError(f"Error getting campaign status: {str(e)}")
    
    def send_letters_for_auction(self, 
                               auction_code: str,
                               letter_content: str,
                               campaign_name: str = None) -> Dict:
        """
        Convenience method to send letters for an auction
        
        Args:
            auction_code: Auction code
            letter_content: HTML content for the letters
            campaign_name: Optional campaign name
            
        Returns:
            Dict containing send results
            
        Raises:
            LobError: If any step fails
        """
        try:
            # Create campaign
            campaign = self.create_campaign(
                name=campaign_name or f"Neighbor Letters - Auction {auction_code}",
                description=f"Neighbor notification letters for auction {auction_code}"
            )
            
            # Create creative
            creative = self.create_creative(
                campaign_id=campaign['id'],
                content=letter_content,
                description=f"Letter template for auction {auction_code}"
            )
            
            # Load addresses
            addresses = self.load_addresses(auction_code)
            
            # Send campaign
            result = self.send_campaign(
                campaign_id=campaign['id'],
                creative_id=creative['id'],
                addresses=addresses
            )
            
            return {
                'campaign_id': campaign['id'],
                'creative_id': creative['id'],
                'addresses_sent': len(addresses),
                'status': result['status']
            }
            
        except Exception as e:
            logger.error(f"Error sending letters for auction {auction_code}: {str(e)}")
            raise

class LobUtilityClient:
    """Client for interacting with Lob API for utility tasks."""
    
    def __init__(self, use_test_key: bool = False):
        """Initialize Lob client with appropriate API key."""
        if use_test_key:
            lob.api_key = os.getenv('LOB_TEST_API_KEY')
        else:
            lob.api_key = os.getenv('LOB_API_KEY')
    
    def verify_address(self, address: Address) -> Dict[str, Any]:
        """Verify a single address using Lob's US Verification API."""
        try:
            verification = lob.USVerification.create(
                primary_line=address.address_line1,
                city=address.address_city,
                state=address.address_state,
                zip_code=address.address_zip
            )
            return {
                'valid': verification.deliverability == 'deliverable',
                'deliverability': verification.deliverability,
                'details': verification
            }
        except Exception as e:
            raise LobAPIError(f"Address verification failed: {str(e)}")
    
    def create_letter(self, to_address: Address, html_content: str) -> Dict[str, Any]:
        """Create a letter using Lob's API."""
        try:
            letter = lob.Letter.create(
                description="Neighbor Letter",
                to_address={
                    'name': to_address.name,
                    'address_line1': to_address.address_line1,
                    'address_city': to_address.address_city,
                    'address_state': to_address.address_state,
                    'address_zip': to_address.address_zip
                },
                from_address={
                    'name': 'McLemore Auction Company',
                    'address_line1': '2450 Atrium Way',
                    'address_city': 'Nashville',
                    'address_state': 'TN',
                    'address_zip': '37214'
                },
                file=html_content,
                color=True,
                double_sided=True,
                return_envelope=False
            )
            return letter
        except Exception as e:
            raise LobAPIError(f"Letter creation failed: {str(e)}")
    
    def send_batch(self, addresses: List[Address], html_template: str, merge_variables: Dict[str, str]) -> Dict[str, Any]:
        """Send a batch of letters using Lob's API."""
        try:
            # Create the HTML template
            template = lob.Template.create(
                description="Neighbor Letter Template",
                html=html_template
            )
            
            # Create address list for the batch
            to_addresses = [{
                'name': addr.name,
                'address_line1': addr.address_line1,
                'address_city': addr.address_city,
                'address_state': addr.address_state,
                'address_zip': addr.address_zip,
                'merge_variables': merge_variables
            } for addr in addresses]
            
            # Create the batch job
            batch_job = lob.Letter.create_multi(
                description="Neighbor Letters Batch",
                to=to_addresses,
                from_address={
                    'name': 'McLemore Auction Company',
                    'address_line1': '2450 Atrium Way',
                    'address_city': 'Nashville',
                    'address_state': 'TN',
                    'address_zip': '37214'
                },
                template_id=template.id,
                color=True,
                double_sided=True,
                return_envelope=False
            )
            return batch_job
        except Exception as e:
            raise LobAPIError(f"Batch send failed: {str(e)}")

class LobAPIError(Exception):
    """Custom exception for Lob API errors."""
    pass

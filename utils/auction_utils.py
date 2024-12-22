"""
Utility functions for handling auction-related data.
"""
import re
import logging
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class ManagerInfo:
    """Container for auction manager information"""
    name: str = ''
    phone: str = ''
    email: str = ''
    
    def is_complete(self) -> bool:
        """Check if all manager info fields are populated"""
        return bool(self.name and self.phone and self.email)
    
    def format_contact_info(self) -> str:
        """Format manager contact information for display"""
        if not self.is_complete():
            # Fallback to default contact info
            return ('Please contact <b>Will McLemore</b> at <b>(615) 636-9602</b> or '
                   '<b><a href="mailto:will@mclemoreauction.com">will@mclemoreauction.com</a></b>')
            
        return (f'Please contact <b>{self.name}</b> at <b>{self.phone}</b> or '
                f'<b><a href="mailto:{self.email}">{self.email}</a></b>')

def extract_manager_info(description: str) -> ManagerInfo:
    """
    Extract manager information from auction description HTML.
    
    Note: This function relies on specific HTML formatting in the description.
    If the AuctionMethod API changes their HTML structure, this function may need to be updated.
    
    Args:
        description: HTML description from auction details
        
    Returns:
        ManagerInfo object with extracted information
    """
    manager = ManagerInfo()
    
    if not description or 'Auction Manager:' not in description:
        logger.debug("No manager section found in description")
        return manager
        
    try:
        # Extract manager section using BeautifulSoup for better HTML parsing
        soup = BeautifulSoup(description, 'html.parser')
        manager_tag = soup.find(string=re.compile('Auction Manager:'))
        
        if not manager_tag or not manager_tag.parent:
            logger.warning("Could not find manager section with BeautifulSoup")
            return manager
            
        # Get the paragraph containing manager info
        manager_p = manager_tag.parent
        manager_text = manager_p.get_text()
        
        # Extract email
        email_tag = manager_p.find('a', href=re.compile('mailto:'))
        if email_tag and '@mclemoreauction.com' in email_tag['href']:
            manager.email = email_tag['href'].replace('mailto:', '')
            logger.debug(f"Found manager email: {manager.email}")
            
        # Extract phone using regex
        phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', manager_text)
        if phone_match:
            manager.phone = phone_match.group()
            logger.debug(f"Found manager phone: {manager.phone}")
            
        # Extract name - it's usually between "Auction Manager:" and the phone/email
        name_text = manager_text.split('Auction Manager:')[-1]
        # Remove phone and email from name text
        if manager.phone:
            name_text = name_text.replace(manager.phone, '')
        if manager.email:
            name_text = name_text.replace(manager.email, '')
            
        # Clean and extract name
        name_parts = [p.strip() for p in name_text.split() if p.strip()]
        if name_parts:
            manager.name = ' '.join(name_parts)
            logger.debug(f"Found manager name: {manager.name}")
            
    except Exception as e:
        logger.error(f"Error extracting manager info: {str(e)}")
        logger.debug(f"Description content: {description[:200]}...")
        
    return manager

def clean_auction_description(description: str) -> str:
    """
    Clean HTML from auction description and remove manager section.
    
    Args:
        description: HTML description from auction details
        
    Returns:
        str: Cleaned description text
    """
    try:
        # Remove manager section first
        if 'Auction Manager:' in description:
            description = description.split('<p><b>Auction Manager:')[0]
            
        # Parse and clean remaining HTML
        soup = BeautifulSoup(description, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
            
        # Get text and clean whitespace
        text = soup.get_text(separator=' ')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return ' '.join(lines)
        
    except Exception as e:
        logger.error(f"Error cleaning description: {str(e)}")
        # Return original description with basic HTML stripping as fallback
        return re.sub('<[^<]+?>', '', description)

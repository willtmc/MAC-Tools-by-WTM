"""Validation functions for neighbor letters module."""
import os
import logging
from pathlib import Path
from flask import current_app
from auction_api import AuctionMethodAPI, AuctionNotFoundError, AuctionAPIError
import pandas as pd

# Get module logger
logger = logging.getLogger(__name__)

def validate_letter_request(auction_code, letter_content=None, check_csv=True):
    """
    Validate letter request parameters.
    
    Args:
        auction_code (str): Auction code to validate
        letter_content (str, optional): Letter content to validate
        check_csv (bool): Whether to check for CSV file existence
        
    Returns:
        list: List of validation error messages, empty if valid
    """
    errors = []
    
    # Validate auction code
    if not auction_code:
        errors.append('Auction code is required')
        return errors
        
    if auction_code.strip() == '':
        errors.append('Auction code cannot be blank')
        return errors
        
    # Validate auction exists
    try:
        auction_api = AuctionMethodAPI()
        auction = auction_api.get_auction_details(auction_code)
        if not auction:
            errors.append('Auction not found')
            return errors
    except AuctionAPIError as e:
        errors.append(f'Error validating auction: {str(e)}')
        return errors
        
    # Validate letter content if provided
    if letter_content is not None:
        valid, error = validate_letter_content(letter_content)
        if not valid:
            errors.append(error)
            return errors
            
    # Validate CSV exists if required
    if check_csv:
        valid, error = validate_csv_exists(auction_code)
        if not valid:
            errors.append(error)
            return errors
            
    return errors

def validate_csv_data(data):
    """
    Validate CSV data.
    
    Args:
        data (pandas.DataFrame): DataFrame containing CSV data
        
    Returns:
        tuple: (is_valid, errors)
            - is_valid (bool): Whether the data is valid
            - errors (list): List of error messages
    """
    errors = []
    
    # Check required columns
    required_cols = ['name', 'address_line1', 'address_city', 'address_state', 'address_zip']
    missing_cols = [col for col in required_cols if col not in data.columns]
    
    if missing_cols:
        errors.append(f'Missing required columns: {", ".join(missing_cols)}')
        return False, errors
        
    # Check for empty values in required columns
    for col in required_cols:
        if data[col].isnull().any():
            errors.append(f'Column {col} contains empty values')
            return False, errors
            
    return True, errors

def validate_letter_content(content):
    """
    Validate letter content has required placeholders.
    
    Args:
        content (str): The letter HTML content
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not content:
        return False, 'Letter content is required'
        
    if not isinstance(content, str):
        return False, 'Letter content must be a string'
        
    # Check for required placeholders
    required_placeholders = [
        '{{name}}',
        '{{address_line1}}',
        '{{address_city}}',
        '{{address_state}}',
        '{{address_zip}}',
        '{{auction_title}}',
        '{{auction_date}}',
        '{{auction_time}}',
        '{{auction_location}}'
    ]
    
    missing_placeholders = []
    for placeholder in required_placeholders:
        if placeholder not in content:
            missing_placeholders.append(placeholder)
            
    if missing_placeholders:
        return False, f'Missing required placeholders: {", ".join(missing_placeholders)}'
        
    # Basic HTML validation
    if not content.strip().startswith('<!DOCTYPE html>'):
        return False, 'Letter content must be valid HTML starting with <!DOCTYPE html>'
        
    if '<html' not in content or '</html>' not in content:
        return False, 'Letter content must contain <html> tags'
        
    return True, None

def validate_auction_code(auction_code):
    """
    Validate auction code format and existence.
    
    Args:
        auction_code (str): The auction code to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not auction_code:
        return False, 'Auction code is required'
        
    if auction_code.strip() == '':
        return False, 'Auction code cannot be blank'
        
    try:
        auction_api = AuctionMethodAPI()
        auction = auction_api.get_auction_details(auction_code)
        if not auction:
            return False, 'Could not find auction'
        return True, None
    except AuctionAPIError as e:
        return False, f'Error validating auction: {str(e)}'

def validate_csv_exists(auction_code):
    """
    Validate that processed CSV exists for auction.
    
    Args:
        auction_code (str): The auction code to check
        
    Returns:
        tuple: (is_valid, error_message)
    """
    data_dir = Path(current_app.config['DATA_FOLDER'])
    csv_path = data_dir / f'{auction_code}_processed.csv'
    
    if not csv_path.exists():
        return False, 'No processed CSV file found for this auction'
        
    try:
        pd.read_csv(csv_path)
        return True, None
    except Exception as e:
        return False, f'Error reading CSV file: {str(e)}'

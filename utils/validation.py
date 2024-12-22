"""Validation utilities for the application."""
import re
from typing import Dict, List, Tuple, Union

def validate_auction_code(auction_code: str) -> Dict[str, Union[bool, List[str]]]:
    """
    Validate auction code format.
    
    Args:
        auction_code: Auction code to validate
        
    Returns:
        Dict with validation result and any errors
    """
    errors = []
    
    if not auction_code:
        errors.append("Auction code is required")
        return {"valid": False, "errors": errors}
        
    # Remove whitespace
    auction_code = auction_code.strip()
    
    # Check format (YYYY-XXXX where XXXX is alphanumeric)
    pattern = r'^\d{4}-[A-Za-z0-9]{4}$'
    if not re.match(pattern, auction_code):
        errors.append("Invalid auction code format. Must be YYYY-XXXX where XXXX is alphanumeric")
        
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def validate_letter_content(content: str) -> Dict[str, Union[bool, List[str]]]:
    """
    Validate letter content.
    
    Args:
        content: HTML content to validate
        
    Returns:
        Dict with validation result and any errors
    """
    errors = []
    
    if not content:
        errors.append("Letter content is required")
        return {"valid": False, "errors": errors}
        
    # Check for required placeholders
    required_placeholders = [
        "{{name}}",
        "{{address_line1}}",
        "{{address_city}}",
        "{{address_state}}",
        "{{address_zip}}"
    ]
    
    for placeholder in required_placeholders:
        if placeholder not in content:
            errors.append(f"Missing required placeholder: {placeholder}")
            
    # Check for basic HTML structure
    if not content.strip().startswith("<!DOCTYPE html>"):
        errors.append("Letter content must start with <!DOCTYPE html>")
        
    if "<html" not in content:
        errors.append("Letter content must contain <html> tag")
        
    if "<body" not in content:
        errors.append("Letter content must contain <body> tag")
        
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

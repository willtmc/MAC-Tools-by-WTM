"""
Tests for neighbor letters functionality
"""
import pytest
from flask import url_for
from unittest.mock import patch

@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_empty_code(mock_api, client):
    """Test edit_letter with empty auction code."""
    response = client.get('/neighbor-letters/edit/')
    assert response.status_code == 404  # Should 404 for empty code in URL
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_blank_code(mock_api, client):
    """Test edit_letter with blank auction code."""
    response = client.get('/neighbor-letters/edit/   ')
    assert response.status_code == 302  # Should redirect
    assert b'Invalid auction code' in response.data
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_invalid_code(mock_api, client):
    """Test edit_letter with invalid auction code."""
    mock_api.get_auction.return_value = None
    response = client.get('/neighbor-letters/edit/INVALID123')
    assert response.status_code == 302  # Should redirect
    assert b'Could not find auction' in response.data
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_valid_code(mock_api, client, sample_auction_data):
    """Test edit_letter with valid auction code."""
    auction_code = sample_auction_data['auction_code']
    mock_api.get_auction.return_value = {
        'title': 'Test Auction',
        'description': 'Test Description',
        'location': '123 Test St',
        'date': '2024-01-01',
        'time': '12:00 PM'
    }
    response = client.get(f'/neighbor-letters/edit/{auction_code}')
    assert response.status_code == 200  # Should succeed
    assert auction_code.encode() in response.data  # Should contain auction code
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_save_content(mock_api, client, sample_auction_data):
    """Test saving letter content."""
    auction_code = sample_auction_data['auction_code']
    mock_api.get_auction.return_value = {
        'title': 'Test Auction',
        'description': 'Test Description',
        'location': '123 Test St',
        'date': '2024-01-01',
        'time': '12:00 PM'
    }
    test_content = 'Test letter content'
    
    # Save content
    response = client.post(f'/neighbor-letters/edit/{auction_code}', 
                         data={'letter_content': test_content})
    assert response.status_code == 302  # Should redirect
    
    # Verify content was saved
    response = client.get(f'/neighbor-letters/edit/{auction_code}')
    assert test_content.encode() in response.data

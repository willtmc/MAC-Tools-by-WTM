"""
Tests for neighbor letters functionality
"""
import pytest
from flask import url_for, session
from unittest.mock import patch

def test_edit_letter_empty_code(client):
    """Test edit_letter with empty auction code."""
    response = client.get('/neighbor_letters/edit/')
    assert response.status_code == 302  # Should redirect to home
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_blank_code(mock_api, client):
    """Test edit_letter with blank auction code."""
    with client.session_transaction() as session:
        session['_flashes'] = []  # Clear any existing flashes
    
    response = client.get('/neighbor_letters/edit/   ', follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid auction code' in response.data
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_invalid_code(mock_api, client):
    """Test edit_letter with invalid auction code."""
    mock_api.get_auction.return_value = None
    with client.session_transaction() as session:
        session['_flashes'] = []  # Clear any existing flashes
    
    response = client.get('/neighbor_letters/edit/INVALID123', follow_redirects=True)
    assert response.status_code == 200
    assert b'Could not find auction' in response.data
    
def test_edit_letter_valid_code(client, sample_auction_data, mock_auction_api):
    """Test edit_letter with valid auction code."""
    with patch('tools.neighbor_letters.routes.auction_api', mock_auction_api):
        auction_code = sample_auction_data['auction_code']
        mock_auction_api.get_auction.return_value = {
            'title': 'Test Auction',
            'description': 'Test Description',
            'location': '123 Test St',
            'date': '2024-01-01',
            'time': '12:00 PM'
        }
        response = client.get(f'/neighbor_letters/edit/{auction_code}')
        assert response.status_code == 200  # Should succeed
        assert auction_code.encode() in response.data  # Should contain auction code
    
def test_edit_letter_save_content(client, sample_auction_data, mock_auction_api):
    """Test saving letter content."""
    with patch('tools.neighbor_letters.routes.auction_api', mock_auction_api):
        auction_code = sample_auction_data['auction_code']
        mock_auction_api.get_auction.return_value = {
            'title': 'Test Auction',
            'description': 'Test Description',
            'location': '123 Test St',
            'date': '2024-01-01',
            'time': '12:00 PM'
        }
        test_content = 'Test letter content'
        
        # First, get the page to get a CSRF token
        with client.session_transaction() as session:
            # Set CSRF token directly in session
            session['_csrf_token'] = 'test_csrf_token'
        
        # Save content with CSRF token
        response = client.post(f'/neighbor_letters/edit/{auction_code}', 
                            data={
                                'letter_content': test_content,
                                'csrf_token': 'test_csrf_token'
                            },
                            follow_redirects=True)
        assert response.status_code == 200
        assert b'Letter template saved successfully' in response.data
        
        # Verify content was saved
        response = client.get(f'/neighbor_letters/edit/{auction_code}')
        assert test_content.encode() in response.data

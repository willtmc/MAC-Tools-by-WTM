"""
Tests for neighbor letters functionality
"""
import pytest
from flask import url_for
from unittest.mock import patch

@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_empty_code(mock_api, client):
    """Test edit_letter with empty auction code."""
    response = client.get('/neighbor_letters/edit/')
    assert response.status_code == 404  # Should 404 for empty code in URL
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_blank_code(mock_api, client):
    """Test edit_letter with blank auction code."""
    response = client.get('/neighbor_letters/edit/   ')
    assert response.status_code == 302  # Should redirect
    assert b'Invalid auction code' in response.data
    
@patch('tools.neighbor_letters.routes.auction_api')
def test_edit_letter_invalid_code(mock_api, client):
    """Test edit_letter with invalid auction code."""
    mock_api.get_auction.return_value = None
    response = client.get('/neighbor_letters/edit/INVALID123')
    assert response.status_code == 302  # Should redirect
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
        
        # Get CSRF token
        response = client.get(f'/neighbor_letters/edit/{auction_code}')
        csrf_token = response.data.split(b'name="csrf_token" value="')[1].split(b'"')[0]
        
        # Save content
        response = client.post(f'/neighbor_letters/edit/{auction_code}', 
                            data={
                                'letter_content': test_content,
                                'csrf_token': csrf_token
                            })
        assert response.status_code == 302  # Should redirect
        
        # Verify content was saved
        response = client.get(f'/neighbor_letters/edit/{auction_code}')
        assert test_content.encode() in response.data

"""
Tests for neighbor letters functionality
"""
import pytest
from flask import url_for

def test_edit_letter_empty_code(client):
    """Test edit_letter with empty auction code."""
    response = client.get('/neighbor-letters/edit/')
    assert response.status_code == 404  # Should 404 for empty code in URL
    
def test_edit_letter_blank_code(client):
    """Test edit_letter with blank auction code."""
    response = client.get('/neighbor-letters/edit/   ')
    assert response.status_code == 302  # Should redirect
    assert b'Invalid auction code' in response.data
    
def test_edit_letter_invalid_code(client):
    """Test edit_letter with invalid auction code."""
    response = client.get('/neighbor-letters/edit/INVALID123')
    assert response.status_code == 302  # Should redirect
    assert b'Could not find auction' in response.data
    
def test_edit_letter_valid_code(client, sample_auction_data):
    """Test edit_letter with valid auction code."""
    auction_code = sample_auction_data['auction_code']
    response = client.get(f'/neighbor-letters/edit/{auction_code}')
    assert response.status_code == 200  # Should succeed
    assert auction_code.encode() in response.data  # Should contain auction code
    
def test_edit_letter_save_content(client, sample_auction_data):
    """Test saving letter content."""
    auction_code = sample_auction_data['auction_code']
    test_content = 'Test letter content'
    
    # Save content
    response = client.post(f'/neighbor-letters/edit/{auction_code}', 
                         data={'letter_content': test_content})
    assert response.status_code == 302  # Should redirect
    
    # Verify content was saved
    response = client.get(f'/neighbor-letters/edit/{auction_code}')
    assert test_content.encode() in response.data

"""
Tests for neighbor letters functionality
"""
import os
import json
import pytest
from flask import url_for, session
from unittest.mock import patch, MagicMock
from pathlib import Path
from auction_api import AuctionMethodAPI
from utils.lob_utils import LobClient, LobAPIError

# Sample data for tests
SAMPLE_LETTER_CONTENT = """<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .letter { max-width: 800px; margin: 0 auto; padding: 20px; }
    </style>
</head>
<body>
    <div class="letter">
        <p>Dear {{name}},</p>
        <p>Join us for {{auction_title}} on {{auction_date}} at {{auction_time}}.</p>
        <p>Location: {{auction_location}}</p>
        <p>{{address_line1}}<br>{{address_city}}, {{address_state}} {{address_zip}}</p>
    </div>
</body>
</html>"""

SAMPLE_CSV_CONTENT = """name,address_line1,address_city,address_state,address_zip
John Doe,123 Main St,Nashville,TN,37203
Jane Smith,456 Oak Ave,Nashville,TN,37204"""

SAMPLE_AUCTION_DATA = {
    'auction_code': '2023-TEST',
    'title': 'Test Property Auction',
    'description': 'Beautiful test property for sale',
    'location': '789 Test Blvd, Nashville, TN',
    'date': '2024-01-15',
    'time': '2:00 PM CST'
}

@pytest.fixture
def mock_auction_api(monkeypatch):
    """Mock AuctionMethodAPI."""
    mock_api = MagicMock()
    mock_api.get_auction_details.return_value = SAMPLE_AUCTION_DATA
    monkeypatch.setattr('tools.neighbor_letters.routes.AuctionMethodAPI', lambda: mock_api)
    return mock_api

@pytest.fixture
def mock_lob_client(monkeypatch):
    """Mock LobClient."""
    mock_client = MagicMock()
    monkeypatch.setattr('tools.neighbor_letters.routes.LobClient', lambda: mock_client)
    return mock_client

def test_edit_letter_empty_code(client):
    """Test edit_letter with empty auction code."""
    response = client.get('/neighbor_letters/edit/', follow_redirects=True)
    assert response.status_code == 200
    assert b'Auction code is required' in response.data

def test_edit_letter_blank_code(client, mock_auction_api):
    """Test edit_letter with blank auction code."""
    response = client.get('/neighbor_letters/edit/   ', follow_redirects=True)
    assert response.status_code == 200
    assert b'Auction code cannot be blank' in response.data

def test_edit_letter_invalid_code(client, mock_auction_api):
    """Test edit_letter with invalid auction code."""
    mock_auction_api.get_auction_details.return_value = None
    response = client.get('/neighbor_letters/edit/INVALID123', follow_redirects=True)
    assert response.status_code == 200
    assert b'Could not find auction' in response.data

def test_edit_letter_valid_code(client, mock_auction_api):
    """Test edit_letter with valid auction code."""
    response = client.get(f'/neighbor_letters/edit/{SAMPLE_AUCTION_DATA["auction_code"]}')
    assert response.status_code == 200
    assert b'Edit Letter Template' in response.data
    assert b'Test Property Auction' in response.data

def test_edit_letter_save_content(client, mock_auction_api):
    """Test saving letter content."""
    auction_code = SAMPLE_AUCTION_DATA['auction_code']
    
    with client.session_transaction() as session:
        session['_csrf_token'] = 'test_csrf_token'
        
    response = client.post(f'/neighbor_letters/edit/{auction_code}',
        data={
            'letter_content': SAMPLE_LETTER_CONTENT,
            'csrf_token': 'test_csrf_token'
        },
        follow_redirects=True)
        
    assert response.status_code == 200
    assert b'Letter template saved successfully' in response.data

def test_complete_letter_workflow(client, tmp_path, mock_auction_api, mock_lob_client):
    """
    Test complete letter generation workflow:
    1. Upload CSV
    2. Preview letter
    3. Send letters
    """
    auction_code = SAMPLE_AUCTION_DATA['auction_code']
    
    # Set up test data directory
    data_dir = tmp_path / 'data'
    data_dir.mkdir(parents=True)
    
    # Configure app to use test data directory
    client.application.config['DATA_FOLDER'] = str(data_dir)
    
    # 1. Upload and process CSV
    csv_file = data_dir / 'addresses.csv'
    csv_file.write_text(SAMPLE_CSV_CONTENT)
    
    with client.session_transaction() as session:
        session['_csrf_token'] = 'test_csrf_token'
        
    response = client.post(f'/neighbor_letters/upload/{auction_code}',
        data={
            'file': (csv_file.open('rb'), 'addresses.csv'),
            'csrf_token': 'test_csrf_token'
        },
        content_type='multipart/form-data',
        follow_redirects=True)
        
    assert response.status_code == 200
    assert b'Addresses uploaded and processed successfully' in response.data
    
    # 2. Preview letter
    response = client.get(f'/neighbor_letters/preview/{auction_code}')
    assert response.status_code == 200
    assert b'Preview Letter' in response.data
    assert b'Test Property Auction' in response.data
    
    # 3. Send letters
    mock_lob_client.send_campaign.return_value = {'id': 'test_campaign'}
    response = client.post(f'/neighbor_letters/send/{auction_code}',
        json={'letter_content': SAMPLE_LETTER_CONTENT},
        follow_redirects=True)
        
    assert response.status_code == 200
    assert b'Letters sent successfully' in response.data
    mock_lob_client.send_campaign.assert_called_once()

def test_letter_validation(client, mock_auction_api):
    """Test letter content validation."""
    auction_code = SAMPLE_AUCTION_DATA['auction_code']
    
    # Test missing required placeholders
    invalid_content = """<!DOCTYPE html>
    <html><body>Invalid letter without placeholders</body></html>"""
    
    response = client.post(f'/neighbor_letters/preview/{auction_code}',
        json={'letter_content': invalid_content})
        
    assert response.status_code == 400
    error_data = json.loads(response.data)
    assert error_data['success'] is False
    assert 'Missing required placeholders' in error_data['errors'][0]
    
    # Test invalid HTML
    response = client.post(f'/neighbor_letters/preview/{auction_code}',
        json={'letter_content': 'Not HTML'})
        
    assert response.status_code == 400
    error_data = json.loads(response.data)
    assert error_data['success'] is False
    assert 'Letter content must be valid HTML' in error_data['errors'][0]
    
    # Test valid letter content
    response = client.post(f'/neighbor_letters/preview/{auction_code}',
        json={'letter_content': SAMPLE_LETTER_CONTENT})
        
    assert response.status_code == 200
    assert json.loads(response.data)['success'] is True

def test_error_handling(client, mock_auction_api, mock_lob_client):
    """Test error handling in letter generation."""
    auction_code = SAMPLE_AUCTION_DATA['auction_code']
    
    # Test invalid letter content
    response = client.post(f'/neighbor_letters/edit/{auction_code}',
        data={
            'letter_content': 'Invalid HTML',
            'csrf_token': 'test_csrf_token'
        },
        follow_redirects=True)
        
    assert response.status_code == 200
    assert b'Letter content must be valid HTML' in response.data
    
    # Test missing required placeholders
    response = client.post(f'/neighbor_letters/edit/{auction_code}',
        data={
            'letter_content': '<!DOCTYPE html><html><body>No placeholders</body></html>',
            'csrf_token': 'test_csrf_token'
        },
        follow_redirects=True)
        
    assert response.status_code == 200
    assert b'Missing required placeholders' in response.data
    
    # Test invalid auction code
    response = client.get('/neighbor_letters/edit/INVALID', follow_redirects=True)
    assert response.status_code == 200
    assert b'Could not find auction' in response.data
    
    # Test Lob API error
    mock_lob_client.send_campaign.side_effect = LobAPIError('Lob API error')
    response = client.post(f'/neighbor_letters/send/{auction_code}',
        json={'letter_content': SAMPLE_LETTER_CONTENT},
        follow_redirects=True)
        
    assert response.status_code == 500
    assert b'Error sending campaign' in response.data

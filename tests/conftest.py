"""Test configuration and fixtures."""
import os
import pytest
from pathlib import Path
from flask import Flask
from app import create_app
from unittest.mock import patch, MagicMock

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary instance path
    test_path = Path(__file__).parent / 'test_instance'
    test_path.mkdir(exist_ok=True)
    
    app = create_app({
        'TESTING': True,
        'UPLOAD_FOLDER': str(test_path / 'uploads'),
        'DATA_FOLDER': str(test_path / 'data'),
        'SECRET_KEY': 'test',
        'WTF_CSRF_ENABLED': False
    })
    
    # Create required directories
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['DATA_FOLDER']).mkdir(parents=True, exist_ok=True)
    
    yield app
    
    # Clean up
    import shutil
    shutil.rmtree(test_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def mock_auction_api():
    """Mock auction API."""
    with patch('auction_api.AuctionMethodAPI') as mock:
        mock.return_value.get_auction_details.return_value = {
            'auction_code': 'TEST123',
            'title': 'Test Auction',
            'description': 'Test Description',
            'location': '123 Test St',
            'date': '2024-01-01',
            'time': '12:00 PM'
        }
        yield mock.return_value

@pytest.fixture
def mock_lob_client():
    """Mock Lob API client."""
    with patch('lob.Client') as mock:
        mock.return_value.send_campaign.return_value = MagicMock(id='test_campaign_id')
        yield mock.return_value

@pytest.fixture
def sample_auction_data():
    """Sample auction data."""
    return {
        'auction_code': 'TEST123',
        'title': 'Test Auction',
        'description': 'Test Description',
        'location': '123 Test St',
        'date': '2024-01-01',
        'time': '12:00 PM'
    }

@pytest.fixture
def sample_letter_content():
    """Sample letter content with all required placeholders."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div>
            {{name}}<br>
            {{address_line1}}<br>
            {{address_city}}, {{address_state}} {{address_zip}}
        </div>
        <div>
            <p>{{auction_title}} on {{auction_date}} at {{auction_time}}</p>
            <p>Location: {{auction_location}}</p>
        </div>
    </body>
    </html>
    """

@pytest.fixture
def sample_csv_content():
    """Sample CSV content."""
    return """Name,Address,City,State,Zip
John Doe,123 Main St,Nashville,TN,37203
Jane Smith,456 Oak Ave,Nashville,TN,37204"""

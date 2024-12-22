"""
Test configuration and fixtures
"""
import os
import pytest
from unittest.mock import MagicMock
from app import create_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SECRET_KEY': 'test'
    })
    
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def sample_auction_data():
    """Sample auction data for testing."""
    return {
        'auction_code': 'TEST123',
        'title': 'Test Auction',
        'description': 'Test Description',
        'location': '123 Test St',
        'date': '2024-01-01',
        'time': '12:00 PM',
        'starting_lot': 1,
        'ending_lot': 5
    }

@pytest.fixture
def mock_auction_api():
    """Mock auction API for testing."""
    mock_api = MagicMock()
    mock_api.get_auction.return_value = {
        'auction_code': 'TEST123',
        'title': 'Test Auction',
        'description': 'Test Description',
        'location': '123 Test St',
        'date': '2024-01-01',
        'time': '12:00 PM'
    }
    return mock_api

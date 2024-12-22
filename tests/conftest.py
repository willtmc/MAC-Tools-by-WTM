"""
Shared pytest fixtures for testing
"""
import os
import tempfile
import pytest
import sys
from pathlib import Path
from io import BytesIO
from reportlab.pdfgen import canvas
from unittest.mock import MagicMock

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to store test database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SERVER_NAME': 'localhost.localdomain',
        'PREFERRED_URL_SCHEME': 'http',
        'WTF_CSRF_ENABLED': False  # Disable CSRF for testing
    })

    # Other setup can go here
    yield app

    # Clean up temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def pdf_canvas():
    """Create a PDF canvas for testing.
    
    Returns:
        tuple: (canvas, buffer) where canvas is the ReportLab Canvas object
        and buffer is the BytesIO buffer containing the PDF data.
    """
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer)
    yield c, pdf_buffer
    c.save()
    pdf_buffer.seek(0)

@pytest.fixture
def mock_auction_api():
    """Mock AuctionMethodAPI for testing."""
    mock_api = MagicMock()
    mock_api.get_auction.return_value = {
        'title': 'Test Auction',
        'description': 'Test Description',
        'location': '123 Test St',
        'date': '2024-01-01',
        'time': '12:00 PM'
    }
    return mock_api

@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return """Name,Address,City,State,Zip
John Doe,123 Main St,Springfield,IL,62701
Jane Smith,789 Pine Ave,Springfield,IL,62702
"""

@pytest.fixture
def sample_auction_data():
    """Sample auction data for testing."""
    return {
        'auction_code': 'TEST123',
        'starting_lot': 1,
        'ending_lot': 5
    }

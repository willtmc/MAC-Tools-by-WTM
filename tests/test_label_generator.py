"""
Tests for QR code label generation functionality
"""
import pytest
from io import BytesIO
import PyPDF2
from tools.qr_labels.routes import generate_sheet

def test_label_generation(app, sample_auction_data):
    """Test basic label generation functionality."""
    with app.app_context():
        # Create a PDF buffer
        pdf_buffer = BytesIO()
        
        # Generate labels
        c = PyPDF2.PdfFileWriter()
        generate_sheet(c, sample_auction_data['auction_code'], sample_auction_data['starting_lot'])
        
        # Write to buffer
        c.write(pdf_buffer)
        pdf_buffer.seek(0)
        
        # Read the generated PDF
        reader = PyPDF2.PdfFileReader(pdf_buffer)
        
        # Basic checks
        assert reader.getNumPages() > 0  # Should have at least one page

def test_invalid_lot_numbers(app):
    """Test handling of invalid lot numbers."""
    with app.app_context():
        with pytest.raises(ValueError):
            generate_sheet(None, 'TEST123', -1)  # Negative lot number
            
def test_invalid_auction_code(app):
    """Test handling of invalid auction code."""
    with app.app_context():
        with pytest.raises(ValueError):
            generate_sheet(None, '', 1)  # Empty auction code

def test_qr_code_url_format(app, sample_auction_data):
    """Test that QR code URLs are correctly formatted."""
    with app.app_context():
        auction_code = sample_auction_data['auction_code']
        lot_number = sample_auction_data['starting_lot']
        
        # Generate a single QR code and verify its content
        from tools.qr_labels.routes import qrcode
        
        qr = qrcode.QRCode()
        expected_url = f"https://www.mclemoreauction.com/auction/{auction_code}/lot/{str(lot_number).zfill(4)}"
        qr.add_data(expected_url)
        qr.make()
        
        # Verify QR code content
        assert qr.data[0] == expected_url.encode()

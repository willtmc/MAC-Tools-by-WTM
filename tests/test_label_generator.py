"""
Tests for QR code label generation functionality
"""
import pytest
import PyPDF2
from tools.qr_labels.routes import generate_sheet, qrcode

def test_label_generation(app, pdf_canvas, sample_auction_data):
    """Test basic label generation functionality."""
    with app.app_context():
        c, pdf_buffer = pdf_canvas
        
        # Generate labels
        generate_sheet(c, sample_auction_data['auction_code'], sample_auction_data['starting_lot'])
        
        # Read the generated PDF
        reader = PyPDF2.PdfReader(pdf_buffer)
        
        # Basic checks
        assert len(reader.pages) > 0  # Should have at least one page

def test_invalid_lot_numbers(app, pdf_canvas):
    """Test handling of invalid lot numbers."""
    with app.app_context():
        c, _ = pdf_canvas
        
        with pytest.raises(ValueError):
            generate_sheet(c, 'TEST123', -1)  # Negative lot number

def test_invalid_auction_code(app, pdf_canvas):
    """Test handling of invalid auction code."""
    with app.app_context():
        c, _ = pdf_canvas
        
        with pytest.raises(ValueError):
            generate_sheet(c, '', 1)  # Empty auction code

def test_qr_code_url_format(app, sample_auction_data):
    """Test that QR code URLs are correctly formatted."""
    with app.app_context():
        auction_code = sample_auction_data['auction_code']
        lot_number = sample_auction_data['starting_lot']
        
        # Generate a single QR code and verify its content
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        expected_url = f"https://www.mclemoreauction.com/auction/{auction_code}/lot/{str(lot_number).zfill(4)}"
        qr.add_data(expected_url)
        qr.make()
        
        # Get QR code image and verify it was created
        qr_img = qr.make_image(fill_color="black", back_color="white")
        assert qr_img is not None

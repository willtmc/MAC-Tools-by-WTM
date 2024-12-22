from flask import render_template, request, send_file, current_app, flash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import qrcode
import os
import tempfile
import logging

from . import qr_labels_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_label_inputs(auction_code: str, starting_lot: int, ending_lot: int = None) -> None:
    """
    Validate input parameters for label generation.
    
    Args:
        auction_code: The auction code to validate
        starting_lot: The starting lot number
        ending_lot: The ending lot number (optional, for batch generation)
        
    Raises:
        ValueError: If any input parameter is invalid
    """
    if not auction_code:
        raise ValueError("Auction code cannot be empty")
    if starting_lot < 1:
        raise ValueError("Starting lot number must be greater than 0")
    if ending_lot is not None:
        if ending_lot < starting_lot:
            raise ValueError("Ending lot number must be greater than or equal to starting lot number")
        if ending_lot < 1:
            raise ValueError("Ending lot number must be greater than 0")

@qr_labels_bp.route('/')
def home():
    return render_template('labels.html')

@qr_labels_bp.route('/generate', methods=['GET', 'POST'])
def generate_labels():
    if request.method == 'POST':
        try:
            auction_code = request.form['auction-code']
            starting_lot = int(request.form['starting-lot'])
            ending_lot = int(request.form['ending-lot'])

            # Single validation call for all inputs
            validate_label_inputs(auction_code, starting_lot, ending_lot)

            logger.info(f"Generating labels for auction {auction_code}, lots {starting_lot}-{ending_lot}")

            pdf_file_path = os.path.join(tempfile.gettempdir(), "qr_code_sheet.pdf")
            c = canvas.Canvas(pdf_file_path, pagesize=letter)

            num_sheets = (ending_lot - starting_lot) // 30 + 1
            for i in range(num_sheets):
                generate_sheet(c, auction_code, starting_lot + i * 30)

            c.save()
            logger.info("PDF generated successfully")

            response = send_file(pdf_file_path, as_attachment=True, download_name=f"auction_labels_{auction_code}.pdf")
            response.call_on_close(lambda: os.remove(pdf_file_path))
            return response

        except Exception as e:
            logger.error(f"Error generating labels: {str(e)}")
            flash("Error generating labels. Please check your input and try again.")
            return render_template('labels.html'), 400

    return render_template('labels.html')

def generate_sheet(c, auction_code, starting_lot):
    """Generate a single sheet of QR code labels"""
    try:
        # Validate input for single sheet
        validate_label_inputs(auction_code, starting_lot)
        
        page_width, page_height = 612, 792
        label_width = 189
        label_height = 72
        top_bottom_margin = 36
        side_margin = 20
        
        for row in range(10):
            for col in range(3):
                x_adjustment = 0
                if col == 0:
                    x_adjustment = -9
                elif col == 2:
                    x_adjustment = 9

                lot_number = starting_lot + row * 3 + col
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=1,
                )
                url = f"https://www.mclemoreauction.com/auction/{auction_code}/lot/{str(lot_number).zfill(4)}"
                qr.add_data(url)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white").resize((45, 45))

                temp_file = tempfile.NamedTemporaryFile(delete=False)
                qr_img.save(temp_file, 'PNG')

                x = side_margin + col * label_width + x_adjustment + 6
                y = page_height - top_bottom_margin - row * label_height - 58

                c.drawImage(temp_file.name, x + 130, y, 50, 50)
                c.setFont("Helvetica", 27)
                c.drawString(x + 10, y + 15, f"Lot {str(lot_number).zfill(4)}")
                c.setFont("Helvetica", 12)
                c.drawString(x + 10, y - 10, "www.McLemoreAuction.com")

                # Clean up temporary file
                os.unlink(temp_file.name)

        c.showPage()
        logger.info(f"Generated sheet starting with lot {starting_lot}")
        
    except Exception as e:
        logger.error(f"Error generating sheet for lot {starting_lot}: {str(e)}")
        raise

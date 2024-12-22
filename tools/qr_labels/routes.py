from flask import render_template, request, send_file, current_app, flash, Blueprint
from flask_wtf.csrf import CSRFProtect
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import qrcode
import os
import tempfile
import logging
from config import BASE_AUCTION_URL

qr_labels_bp = Blueprint(
    'qr_labels_bp',
    __name__,
    template_folder='templates'
)

logger = logging.getLogger(__name__)

@qr_labels_bp.route('/')
def home():
    return render_template('qr_labels/labels.html')

@qr_labels_bp.route('/generate', methods=['POST'])
def generate_labels():
    try:
        auction_code = request.form['auction-code']
        starting_lot = int(request.form['starting-lot'])
        ending_lot = int(request.form['ending-lot'])

        if not auction_code:
            raise ValueError("Auction code required")
        if starting_lot < 1 or ending_lot < starting_lot:
            raise ValueError("Lot numbers invalid")

        logger.info(f"Generating labels for {auction_code} from {starting_lot} to {ending_lot}")

        pdf_file_path = os.path.join(tempfile.gettempdir(), "qr_code_sheet.pdf")
        c = canvas.Canvas(pdf_file_path, pagesize=letter)

        # For demonstration, just generate one large sheet:
        generate_sheet(c, auction_code, start_lot=starting_lot, end_lot=ending_lot)
        c.save()

        response = send_file(pdf_file_path, as_attachment=True, download_name=f"auction_labels_{auction_code}.pdf")
        response.call_on_close(lambda: os.remove(pdf_file_path))
        return response

    except Exception as e:
        logger.error(f"Error generating labels: {e}")
        flash(str(e), 'error')
        return render_template('qr_labels/labels.html'), 400

def generate_sheet(c, auction_code, start_lot, end_lot):
    page_width, page_height = 612, 792
    label_width = 189
    label_height = 72
    top_bottom_margin = 36
    side_margin = 20

    current_lot = start_lot
    while current_lot <= end_lot:
        for row in range(10):
            for col in range(3):
                lot_number = current_lot
                if lot_number > end_lot:
                    return  # done

                # Build URL for the lot
                url = f"{BASE_AUCTION_URL}/auction/{auction_code}/lot/{str(lot_number).zfill(4)}"
                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=1)
                qr.add_data(url)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white").resize((45, 45))

                temp_file = tempfile.NamedTemporaryFile(delete=False)
                qr_img.save(temp_file, 'PNG')

                x_pos = side_margin + col * label_width + (0 if col == 1 else (-9 if col == 0 else 9)) + 6
                y_pos = page_height - top_bottom_margin - row * label_height - 58

                c.drawImage(temp_file.name, x_pos + 130, y_pos, 50, 50)
                c.setFont("Helvetica", 27)
                c.drawString(x_pos + 10, y_pos + 15, f"Lot {str(lot_number).zfill(4)}")
                c.setFont("Helvetica", 12)
                c.drawString(x_pos + 10, y_pos - 10, "www.McLemoreAuction.com")

                os.unlink(temp_file.name)
                current_lot += 1
            # Force a new page after each row to keep it simpler
            c.showPage()
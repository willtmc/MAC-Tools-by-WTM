from flask import render_template, request, send_file, current_app
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

from . import label_generator_bp

@label_generator_bp.route('/')
def home():
    return render_template('labels.html')

@label_generator_bp.route('/generate', methods=['POST'])
def generate():
    auction_code = request.form.get('auction-code')
    starting_lot = int(request.form.get('starting-lot'))
    ending_lot = int(request.form.get('ending-lot'))

    # Create a PDF buffer
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Label dimensions and spacing
    label_width = 144  # 2 inches in points
    label_height = 72  # 1 inch in points
    margin_x = 72  # 1 inch margin
    margin_y = 72  # 1 inch margin
    spacing_x = 36  # 0.5 inch spacing between labels
    spacing_y = 36  # 0.5 inch spacing between rows
    
    # Calculate labels per row and number of rows
    page_width, page_height = letter
    labels_per_row = int((page_width - 2 * margin_x + spacing_x) / (label_width + spacing_x))
    rows_per_page = int((page_height - 2 * margin_y + spacing_y) / (label_height + spacing_y))
    
    current_lot = starting_lot
    row = 0
    col = 0
    
    while current_lot <= ending_lot:
        if row >= rows_per_page:
            c.showPage()
            row = 0
            col = 0
        
        # Calculate label position
        x = margin_x + col * (label_width + spacing_x)
        y = page_height - (margin_y + (row + 1) * label_height + row * spacing_y)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=0)
        qr.add_data(f"{auction_code}-{current_lot}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert QR code to bytes
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer)
        qr_buffer.seek(0)
        
        # Draw label border
        c.rect(x, y, label_width, label_height)
        
        # Draw QR code
        qr_size = 50  # Size of QR code in points
        c.drawImage(qr_buffer, x + 5, y + 5, width=qr_size, height=qr_size)
        
        # Draw text
        c.setFont("Helvetica", 10)
        c.drawString(x + qr_size + 10, y + label_height/2, f"{auction_code}")
        c.drawString(x + qr_size + 10, y + label_height/2 - 15, f"Lot {current_lot}")
        
        current_lot += 1
        col += 1
        if col >= labels_per_row:
            col = 0
            row += 1
    
    c.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'labels_{auction_code}_{starting_lot}-{ending_lot}.pdf',
        mimetype='application/pdf'
    )

"""
Shared utilities for PDF and QR code generation
"""
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

class LabelGenerator:
    def __init__(self, auction_code, starting_lot, ending_lot, label_type="standard"):
        self.auction_code = auction_code
        self.starting_lot = starting_lot
        self.ending_lot = ending_lot
        self.label_type = label_type
        self.page_width, self.page_height = letter

    def generate_qr_code(self, lot_number, size=(45, 45)):
        """Generate QR code for a lot number"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1 if self.label_type == "detailed" else 0
        )
        
        # Different QR code content based on label type
        if self.label_type == "detailed":
            url = f"https://www.mclemoreauction.com/auction/{self.auction_code}/lot/{str(lot_number).zfill(4)}"
            qr.add_data(url)
        else:
            qr.add_data(f"{self.auction_code}-{lot_number}")
            
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        if size != (45, 45):
            qr_img = qr_img.resize(size)
            
        return qr_img

    def generate_standard_labels(self, buffer):
        """Generate simple 2"x1" labels"""
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Label dimensions and spacing
        label_width = 144  # 2 inches in points
        label_height = 72  # 1 inch in points
        margin_x = 72
        margin_y = 72
        spacing_x = 36
        spacing_y = 36
        
        # Calculate layout
        labels_per_row = int((self.page_width - 2 * margin_x + spacing_x) / (label_width + spacing_x))
        rows_per_page = int((self.page_height - 2 * margin_y + spacing_y) / (label_height + spacing_y))
        
        current_lot = self.starting_lot
        row = 0
        col = 0
        
        while current_lot <= self.ending_lot:
            if row >= rows_per_page:
                c.showPage()
                row = 0
                col = 0
            
            # Calculate position
            x = margin_x + col * (label_width + spacing_x)
            y = self.page_height - (margin_y + (row + 1) * label_height + row * spacing_y)
            
            # Generate and draw QR code
            qr_img = self.generate_qr_code(current_lot, size=(50, 50))
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer)
            qr_buffer.seek(0)
            
            # Draw label
            c.rect(x, y, label_width, label_height)
            c.drawImage(qr_buffer, x + 5, y + 5, width=50, height=50)
            
            # Draw text
            c.setFont("Helvetica", 10)
            c.drawString(x + 60, y + label_height/2, f"{self.auction_code}")
            c.drawString(x + 60, y + label_height/2 - 15, f"Lot {current_lot}")
            
            current_lot += 1
            col += 1
            if col >= labels_per_row:
                col = 0
                row += 1
        
        c.save()
        buffer.seek(0)
        return buffer

    def generate_detailed_labels(self):
        """Generate detailed labels with URLs (3x10 layout)"""
        pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        c = canvas.Canvas(pdf_file.name, pagesize=letter)
        
        num_sheets = (self.ending_lot - self.starting_lot) // 30 + 1
        for i in range(num_sheets):
            self._generate_detailed_sheet(c, self.starting_lot + i * 30)
        
        c.save()
        return pdf_file.name

    def _generate_detailed_sheet(self, c, starting_lot):
        """Generate a single sheet of detailed labels"""
        try:
            label_width = 189
            label_height = 72
            top_bottom_margin = 36
            side_margin = 20
            
            for row in range(10):
                for col in range(3):
                    x_adjustment = -9 if col == 0 else (9 if col == 2 else 0)
                    lot_number = starting_lot + row * 3 + col
                    
                    if lot_number > self.ending_lot:
                        continue
                        
                    # Generate QR code
                    qr_img = self.generate_qr_code(lot_number)
                    temp_file = tempfile.NamedTemporaryFile(delete=False)
                    qr_img.save(temp_file, 'PNG')
                    
                    # Calculate position
                    x = side_margin + col * label_width + x_adjustment + 6
                    y = self.page_height - top_bottom_margin - row * label_height - 58
                    
                    # Draw label
                    c.drawImage(temp_file.name, x + 130, y, 50, 50)
                    c.setFont("Helvetica", 27)
                    c.drawString(x + 10, y + 15, f"Lot {str(lot_number).zfill(4)}")
                    c.setFont("Helvetica", 12)
                    c.drawString(x + 10, y - 10, "www.McLemoreAuction.com")
                    
                    os.unlink(temp_file.name)
            
            c.showPage()
            logger.info(f"Generated detailed sheet starting with lot {starting_lot}")
            
        except Exception as e:
            logger.error(f"Error generating detailed sheet for lot {starting_lot}: {str(e)}")
            raise

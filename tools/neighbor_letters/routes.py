"""Routes for neighbor letters functionality."""
import os
import json
import csv
from io import StringIO
from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, abort, redirect, url_for
from auction_api import AuctionMethodAPI, AuctionNotFoundError, AuctionAPIError
from utils.lob_utils import LobClient, LobAPIError, Address
from utils.validation import validate_letter_content, validate_auction_code
from pathlib import Path

# Create blueprint
neighbor_letters = Blueprint('neighbor_letters', __name__, url_prefix='/neighbor_letters')

@neighbor_letters.route('/')
def home():
    """Home page."""
    return render_template('neighbor_letters/home.html')

@neighbor_letters.route('/edit/', defaults={'auction_code': None})
@neighbor_letters.route('/edit/<auction_code>')
def edit_letter(auction_code):
    """Edit letter template for an auction."""
    if not auction_code:
        flash('Auction code is required', 'error')
        return redirect(url_for('neighbor_letters.home'))
        
    auction_code = auction_code.strip()
    if not auction_code:
        flash('Auction code cannot be blank', 'error')
        return redirect(url_for('neighbor_letters.home'))
        
    # Get auction details
    api = AuctionMethodAPI()
    auction = api.get_auction_details(auction_code)
    
    if not auction:
        flash('Could not find auction', 'error')
        return redirect(url_for('neighbor_letters.home'))
    
    # Load saved template if it exists
    template_path = os.path.join(current_app.config['DATA_FOLDER'], auction_code, 'template.html')
    letter_content = ''
    if os.path.exists(template_path):
        with open(template_path, 'r') as f:
            letter_content = f.read()
    
    return render_template('neighbor_letters/edit.html',
                         auction_code=auction_code,
                         auction=auction,
                         letter_content=letter_content)

@neighbor_letters.route('/edit/<auction_code>', methods=['POST'])
def save_letter(auction_code):
    """Save letter template."""
    letter_content = request.form.get('letter_content', '')
    
    # Validate content
    validation_result = validate_letter_content(letter_content)
    if not validation_result['valid']:
        flash(validation_result['errors'][0], 'error')
        return redirect(url_for('neighbor_letters.edit_letter', auction_code=auction_code))
    
    # Save template
    data_dir = os.path.join(current_app.config['DATA_FOLDER'], auction_code)
    os.makedirs(data_dir, exist_ok=True)
    
    template_path = os.path.join(data_dir, 'template.html')
    with open(template_path, 'w') as f:
        f.write(letter_content)
    
    flash('Letter template saved successfully', 'success')
    return redirect(url_for('neighbor_letters.edit_letter', auction_code=auction_code))

@neighbor_letters.route('/upload/<auction_code>', methods=['POST'])
def upload_addresses(auction_code):
    """Upload and process CSV file with addresses."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'File must be a CSV'})
    
    try:
        # Read CSV
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        addresses = list(csv.DictReader(stream))
        
        # Verify addresses using Lob
        lob_client = LobClient(use_test_key=current_app.config.get('TESTING', False))
        verified_addresses = []
        invalid_addresses = []
        
        for addr in addresses:
            address = Address(
                name=addr['name'],
                address_line1=addr['address_line1'],
                address_city=addr['address_city'],
                address_state=addr['address_state'],
                address_zip=addr['address_zip']
            )
            
            verification = lob_client.verify_address(address)
            if verification['valid']:
                verified_addresses.append(addr)
            else:
                invalid_addresses.append({
                    'address': addr,
                    'reason': verification['deliverability']
                })
        
        # Save processed addresses
        data_dir = os.path.join(current_app.config['DATA_FOLDER'], auction_code)
        os.makedirs(data_dir, exist_ok=True)
        
        addresses_path = os.path.join(data_dir, 'addresses.json')
        with open(addresses_path, 'w') as f:
            json.dump({
                'valid': verified_addresses,
                'invalid': invalid_addresses
            }, f)
        
        return jsonify({
            'success': True,
            'message': 'Addresses uploaded and processed successfully',
            'valid_count': len(verified_addresses),
            'invalid_count': len(invalid_addresses)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@neighbor_letters.route('/preview/<auction_code>')
def preview_letter(auction_code):
    """Preview letter template with sample addresses."""
    # Get auction details
    api = AuctionMethodAPI()
    auction = api.get_auction_details(auction_code)
    
    if not auction:
        flash('Could not find auction', 'error')
        return redirect(url_for('neighbor_letters.home'))
    
    # Load template and addresses
    template_path = os.path.join(current_app.config['DATA_FOLDER'], auction_code, 'template.html')
    addresses_path = os.path.join(current_app.config['DATA_FOLDER'], auction_code, 'addresses.json')
    
    if not os.path.exists(template_path) or not os.path.exists(addresses_path):
        flash('Missing template or addresses', 'error')
        return redirect(url_for('neighbor_letters.edit_letter', auction_code=auction_code))
    
    with open(template_path, 'r') as f:
        template = f.read()
    
    with open(addresses_path, 'r') as f:
        addresses = json.load(f)
    
    # Get sample addresses for preview
    sample_addresses = addresses['valid'][:2] if addresses['valid'] else []
    
    return render_template('neighbor_letters/preview.html',
                         auction_code=auction_code,
                         auction=auction,
                         template=template,
                         sample_addresses=sample_addresses)

@neighbor_letters.route('/preview/<auction_code>', methods=['POST'])
def validate_preview(auction_code):
    """Validate letter content."""
    content = request.json.get('letter_content', '')
    validation_result = validate_letter_content(content)
    
    if not validation_result['valid']:
        return jsonify({
            'success': False,
            'errors': validation_result['errors']
        }), 400
    
    return jsonify({'success': True})

@neighbor_letters.route('/send/<auction_code>', methods=['POST'])
def send_letters(auction_code):
    """Send letters using Lob API."""
    try:
        # Get auction details
        api = AuctionMethodAPI()
        auction = api.get_auction_details(auction_code)
        
        if not auction:
            return jsonify({
                'success': False,
                'error': 'Could not find auction'
            }), 404
        
        # Load template and addresses
        template_path = os.path.join(current_app.config['DATA_FOLDER'], auction_code, 'template.html')
        addresses_path = os.path.join(current_app.config['DATA_FOLDER'], auction_code, 'addresses.json')
        
        with open(template_path, 'r') as f:
            template = f.read()
        
        with open(addresses_path, 'r') as f:
            addresses_data = json.load(f)
        
        # Convert addresses to Address objects
        addresses = [Address(**addr) for addr in addresses_data['valid']]
        
        # Prepare merge variables
        merge_variables = {
            'auction_title': auction['title'],
            'auction_date': auction['date'],
            'auction_time': auction['time'],
            'auction_location': auction['location']
        }
        
        # Send letters
        lob_client = LobClient(use_test_key=current_app.config.get('TESTING', False))
        result = lob_client.send_batch(addresses, template, merge_variables)
        
        return jsonify({
            'success': True,
            'message': 'Letters sent successfully',
            'details': {
                'campaign_id': result['id'],
                'addresses_sent': len(addresses)
            }
        })
        
    except LobAPIError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error sending letters: {str(e)}'
        }), 500

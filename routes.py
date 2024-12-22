"""Main application routes."""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session, send_file
)

from tools.neighbor_letters.routes import neighbor_letters
from auction_api import AuctionMethodAPI, AuctionNotFoundError, AuctionAPIError
from utils.lob_utils import LobClient, LobAPIError, Address

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize blueprint
bp = Blueprint('main', __name__)

# Initialize APIs
auction_api = None

def init_apis():
    """Initialize API clients."""
    global auction_api
    try:
        auction_api = AuctionMethodAPI()
    except Exception as e:
        logger.error(f"Failed to initialize AuctionMethodAPI: {str(e)}")
        raise

@bp.route('/')
def index():
    """Home page."""
    return render_template('index.html')

@bp.route('/logout')
def logout():
    """Logout route."""
    session.clear()
    return redirect(url_for('main.index'))

@bp.route('/auctions/<auction_code>')
def auction_details(auction_code):
    """Show auction details."""
    try:
        # Get auction details
        auction = auction_api.get_auction_details(auction_code)
        if not auction:
            flash('Could not find auction', 'error')
            return redirect(url_for('main.index'))
            
        return render_template(
            'auction_details.html',
            auction=auction
        )
        
    except AuctionNotFoundError:
        flash('Could not find auction', 'error')
        return redirect(url_for('main.index'))
        
    except AuctionAPIError as e:
        flash(f'Error getting auction details: {str(e)}', 'error')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        logger.error(f"Error getting auction details: {str(e)}")
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('main.index'))

@bp.route('/auctions/search')
def search_auctions():
    """Search auctions."""
    try:
        # Get search query
        query = request.args.get('q', '')
        if not query:
            return jsonify({
                'success': True,
                'auctions': []
            })
            
        # Search auctions
        auctions = auction_api.search_auctions(query)
        
        return jsonify({
            'success': True,
            'auctions': auctions
        })
        
    except AuctionAPIError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Error searching auctions: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred'
        }), 500

@bp.route('/download/<path:filename>')
def download_file(filename):
    """Download a file."""
    try:
        # Get file path
        file_path = Path('data') / filename
        if not file_path.exists():
            flash('File not found', 'error')
            return redirect(url_for('main.index'))
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('main.index'))

@bp.route('/process', methods=['POST'])
def process():
    """Process uploaded CSV file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            logger.error("No file in request.files")
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['file']
        if not file or not file.filename:
            logger.error("Empty file object or no filename")
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        # Check file extension
        if not file.filename.lower().endswith('.csv'):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'success': False, 'message': 'Only CSV files are allowed'}), 400

        # Get auction code
        auction_code = request.form.get('auction_code')
        if not auction_code:
            logger.error("No auction code provided")
            return jsonify({'success': False, 'message': 'No auction code provided'}), 400

        logger.info(f"Processing file: {file.filename}")
        logger.info(f"Auction code: {auction_code}")
        
        try:
            # Read CSV file with flexible encoding detection
            df = read_csv_flexibly(file)
            
            # Process the CSV data
            processor = CSVProcessor()
            result_df, stats = processor.process_csv_data(df)
            
            # Store results in session
            session['processed_data'] = result_df.to_dict('records')
            session['auction_code'] = auction_code
            
            return jsonify({
                'success': True,
                'message': 'CSV processed successfully',
                'stats': stats
            })
            
        except CSVReadError as e:
            logger.error(f"Error reading CSV: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error reading CSV file: {str(e)}'
            }), 400
        except pd.errors.EmptyDataError:
            logger.error("Empty CSV file provided")
            return jsonify({
                'success': False,
                'message': 'The CSV file is empty'
            }), 400
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

@bp.route('/view-confirmation/<auction_code>')
def view_confirmation(auction_code):
    """View confirmation page with processed addresses"""
    try:
        if 'processed_data' not in session:
            return render_template('error.html', message='No processed data found. Please upload a CSV file first.')
            
        processed_data = session['processed_data']
        return render_template('confirmation.html', addresses=processed_data, auction_code=auction_code)
        
    except Exception as e:
        logger.error(f"Error viewing confirmation: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template('error.html', message=f'Error viewing confirmation: {str(e)}')

@bp.route('/send-letters/<auction_code>', methods=['POST'])
def send_letters(auction_code):
    """Send letters through Lob"""
    try:
        if 'processed_data' not in session:
            return jsonify({
                'success': False,
                'message': 'No processed data found. Please upload a CSV file first.'
            }), 400
            
        processed_data = session['processed_data']
        
        # Initialize Lob client
        lob_client = LobClient(use_test_key=False)
        
        # Convert addresses to Address objects
        addresses = [Address(
            name=addr['name'],
            address_line1=addr['address_line1'],
            address_city=addr['address_city'],
            address_state=addr['address_state'],
            address_zip=addr['address_zip']
        ) for addr in processed_data]
        
        # Verify addresses using Lob
        verified_addresses = []
        invalid_addresses = []
        
        for addr in addresses:
            verification = lob_client.verify_address(addr)
            if verification['valid']:
                verified_addresses.append(addr)
            else:
                invalid_addresses.append({
                    'address': addr,
                    'reason': verification['deliverability']
                })
        
        # Send letters
        result = lob_client.send_batch(verified_addresses, 'letter_template.html', {})
        
        return jsonify({
            'success': True,
            'message': 'Letters sent successfully',
            'details': {
                'campaign_id': result['id'],
                'addresses_sent': len(verified_addresses)
            }
        })
        
    except LobAPIError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error sending letters: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error sending letters: {str(e)}'
        }), 500

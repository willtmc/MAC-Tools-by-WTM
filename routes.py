from flask import Blueprint, render_template
import pandas as pd
import logging
import traceback
from typing import Dict
import io
import csv
import os

from csv_processor import CSVProcessor
from auction_api import AuctionMethodAPI
from letter_generator import LetterGenerator

# Get module logger
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# Initialize API clients
auction_api = None
letter_generator = None

def init_apis():
    pass

@bp.route('/')
def home():
    return render_template('main.html')

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
            # Read the file content
            file_content = file.read()
            
            # Try UTF-8 with BOM first
            try:
                file_content_str = file_content.decode('utf-8-sig')
                logger.info("Successfully decoded file with UTF-8-sig")
            except UnicodeDecodeError:
                # If that fails, try plain UTF-8
                try:
                    file_content_str = file_content.decode('utf-8')
                    logger.info("Successfully decoded file with UTF-8")
                except UnicodeDecodeError:
                    # If both fail, try Latin-1 as a fallback
                    file_content_str = file_content.decode('latin-1')
                    logger.info("Successfully decoded file with Latin-1")
            
            logger.info("File content read successfully")
            
            # Try to detect the CSV dialect
            try:
                sniffer = csv.Sniffer()
                has_header = sniffer.has_header(file_content_str[:1024])
                dialect = sniffer.sniff(file_content_str[:1024])
                logger.info(f"Detected CSV dialect: delimiter='{dialect.delimiter}', quotechar='{dialect.quotechar}'")
                logger.info(f"Has header: {has_header}")
            except Exception as e:
                logger.warning(f"Could not detect CSV dialect: {str(e)}. Using default settings.")
                dialect = None
                has_header = True
            
            # Read CSV with pandas
            try:
                # First try with detected dialect
                if dialect:
                    try:
                        df = pd.read_csv(io.StringIO(file_content_str), 
                                       delimiter=dialect.delimiter,
                                       quotechar=dialect.quotechar if dialect.quotechar else '"',
                                       escapechar='\\',
                                       on_bad_lines='skip',
                                       encoding_errors='replace',
                                       dtype=str,
                                       header=0 if has_header else None)
                        logger.info("Successfully read CSV with detected dialect")
                    except Exception as e:
                        logger.warning(f"Failed to read with detected dialect: {str(e)}")
                        df = None
                
                # If that fails, try common delimiters
                if df is None:
                    for delimiter in [',', ';', '\t']:
                        try:
                            df = pd.read_csv(io.StringIO(file_content_str),
                                           delimiter=delimiter,
                                           quotechar='"',
                                           escapechar='\\',
                                           on_bad_lines='skip',
                                           encoding_errors='replace',
                                           dtype=str,
                                           header=0 if has_header else None)
                            logger.info(f"Successfully read CSV with delimiter: '{delimiter}'")
                            break
                        except Exception as e:
                            logger.warning(f"Failed to read CSV with delimiter '{delimiter}': {str(e)}")
                            continue
                    else:
                        raise ValueError("Could not read CSV with any common delimiter")
                
                if df is None or len(df) == 0:
                    raise ValueError("CSV file is empty or could not be read")
                
                logger.info(f"Successfully read CSV with shape: {df.shape}")
                logger.info(f"Columns: {list(df.columns)}")
                
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
                
            except Exception as e:
                logger.error(f"Error reading CSV: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return jsonify({
                    'success': False,
                    'message': f'Error reading CSV file: {str(e)}'
                }), 400
                
        except Exception as e:
            logger.error(f"Error processing file content: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'Error processing file content: {str(e)}'
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
        
        # Initialize letter generator if needed
        global letter_generator
        if not letter_generator:
            letter_generator = LetterGenerator()
            
        # Send letters
        results = letter_generator.send_letters(processed_data, auction_code)
        
        return jsonify({
            'success': True,
            'message': 'Letters sent successfully',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error sending letters: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error sending letters: {str(e)}'
        }), 500

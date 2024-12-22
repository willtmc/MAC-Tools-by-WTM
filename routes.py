import os
from flask import Blueprint, render_template, jsonify, request, session
import pandas as pd
import logging
import traceback
from typing import Dict
import io
import csv
import os
from utils.csv_utils import read_csv_flexibly, CSVReadError
from csv_processor import CSVProcessor
from auction_api import AuctionMethodAPI
from letter_generator import LetterGenerator
from config import BASE_AUCTION_URL, BASE_TOOLS_URL

# Get module logger
logger = logging.getLogger(__name__)

# Initialize API clients
try:
    auction_api = AuctionMethodAPI()
    logger.info("Successfully initialized AuctionMethodAPI")
except ValueError as e:
    logger.error(f"Could not initialize AuctionMethodAPI: {str(e)}")
    auction_api = None

letter_generator = None

def init_apis():
    pass

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return render_template('index.html')

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

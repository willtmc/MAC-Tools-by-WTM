import os
from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, abort, redirect, url_for
import pandas as pd
import logging
import traceback
from typing import Dict
import io
from datetime import datetime
from auction_api import AuctionMethodAPI
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
from utils.csv_utils import read_csv_flexibly, CSVReadError
from utils.auction_utils import extract_manager_info, clean_auction_description
from csv_processor import CSVProcessor, CSVProcessorError, CSVFormatError
from config import BASE_AUCTION_URL, SIGNATURE_IMAGE_URL

from . import neighbor_letters_bp

# Get module logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize API client
try:
    auction_api = AuctionMethodAPI()
    logger.info("Successfully initialized AuctionMethodAPI")
except ValueError as e:
    logger.error(f"Could not initialize AuctionMethodAPI: {str(e)}")
    auction_api = None

def generate_default_letter(auction_details, auction_date, auction_time, sample_address=None):
    """
    Generate default letter content with auction details
    
    Args:
        auction_details: Dictionary containing auction information
        auction_date: Formatted auction date string
        auction_time: Formatted auction time string
        sample_address: Optional sample address for preview
        
    Returns:
        str: Generated HTML letter content
    """
    if not auction_details:
        return "Letter content will be generated when auction details are available."
    
    # Format current date
    current_date = datetime.now().strftime('%B %d, %Y')
    
    # Extract and validate manager info
    description = auction_details.get('description', '')
    manager = extract_manager_info(description)
    
    # Clean description
    description = clean_auction_description(description)
    
    # Format property address
    property_address = auction_details.get('location', '')
    
    # Format bidding end time
    bidding_end = auction_date
    if auction_time:
        bidding_end += f" at {auction_time}"
    
    letter = f"""
    <p>{current_date}</p>

    <p>RE: Upcoming Auction of <b>{auction_details.get('title', '')}</b></p>

    <p>Dear Sir or Madam:</p>

    <p>{description}</p>

    <p>The property address is <b>{property_address}.</b></p>

    <p>Based on our research, you own real estate near the property we are selling.</p>

    <p>The auction will take place on our website at <b><a href="{BASE_AUCTION_URL}">{BASE_AUCTION_URL}</a></b>. You may register to bid at <b><a href="{BASE_AUCTION_URL}/register">{BASE_AUCTION_URL}/register</a></b>.</p>

    <p>Note: <b>This auction closes {bidding_end}.</b></p>

    <p>{manager.format_contact_info()} to schedule an appointment to view this property.</p>

    <p><b>Please scan the QR code to visit our website.</b></p>

    <ul class="signature-list">
        <li class="signature-paragraph">
            Yours Truly,<br>
            <img src="{SIGNATURE_IMAGE_URL}" alt="Signature" class="signature-image"><br>
            <b>Will McLemore, CAI</b><br>
            <b><a href="mailto:will@mclemoreauction.com">will@mclemoreauction.com</a> | (615) 636-9602</b>
        </li>
    </ul>
    """
    
    return letter

@neighbor_letters_bp.route('/')
def home():
    return render_template('letters.html')

@neighbor_letters_bp.route('/process', methods=['POST'])
def process():
    """Process uploaded CSV file"""
    try:
        logger.info("Starting file processing")
        
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
            return jsonify({'success': False, 'message': 'Auction code is required'}), 400

        logger.info(f"Processing file for auction {auction_code}")

        # Read CSV file with flexible encoding detection
        try:
            df = read_csv_flexibly(file)
            logger.info(f"Successfully read CSV with {len(df)} rows")
            
        except CSVReadError as e:
            logger.error(f"Error reading CSV: {str(e)}")
            return jsonify({'success': False, 'message': f'Error reading CSV file: {str(e)}. Please check the format.'}), 400
        except pd.errors.EmptyDataError:
            logger.error("Empty CSV file provided")
            return jsonify({'success': False, 'message': 'The CSV file is empty'}), 400

        # Process the data using CSVProcessor
        try:
            processor = CSVProcessor()
            processed_df, stats = processor.process_csv_data(df)
            
            # Save processed data
            output_dir = os.path.join(current_app.root_path, 'data', auction_code)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'processed_addresses.csv')
            processed_df.to_csv(output_file, index=False)

            logger.info(f"Successfully processed and saved {len(processed_df)} addresses")

            return jsonify({
                'success': True,
                'message': 'File processed successfully',
                'total_rows': stats.total_rows,
                'processed_rows': stats.processed_rows,
                'skipped_rows': stats.skipped_rows,
                'format_detected': stats.format_detected,
                'cemetery_records_skipped': stats.cemetery_records_skipped,
                'duplicate_rows': stats.duplicate_rows
            })

        except CSVFormatError as e:
            logger.error(f"Invalid CSV format: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 400
        except CSVProcessorError as e:
            logger.error(f"Error processing CSV: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 400
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}\n{traceback.format_exc()}")
            return jsonify({'success': False, 'message': f'Error processing data: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'}), 500

@neighbor_letters_bp.route('/edit/<auction_code>')
def edit_letter(auction_code):
    """Edit letter template for the auction"""
    try:
        # Check if the processed data exists
        data_file = os.path.join(current_app.root_path, 'data', auction_code, 'processed_addresses.csv')
        if not os.path.exists(data_file):
            flash('No processed data found. Please upload a CSV file first.', 'error')
            return redirect(url_for('neighbor_letters_bp.home'))
        
        # Get auction details from API
        auction_details = None
        auction_date = ''
        auction_time = ''
        
        if auction_api:
            try:
                logger.info(f"Fetching auction details for {auction_code}")
                auction_details = auction_api.get_auction_details(auction_code)
                logger.info(f"Got auction details: {auction_details}")
                
                # Parse date and time
                if auction_details.get('date'):
                    auction_date = datetime.strptime(auction_details['date'], '%Y-%m-%d').strftime('%Y-%m-%d')
                    logger.info(f"Parsed auction date: {auction_date}")
                if auction_details.get('time'):
                    auction_time = auction_details['time']
                    logger.info(f"Got auction time: {auction_time}")
            except Exception as e:
                logger.error(f"Could not fetch auction details: {str(e)}\n{traceback.format_exc()}")
                flash(f'Warning: Could not fetch auction details: {str(e)}', 'warning')
        else:
            logger.warning("Auction API not initialized")
        
        # Read the processed data
        df = pd.read_csv(data_file)
        sample_address = df.iloc[0].to_dict() if len(df) > 0 else None
        logger.info(f"Sample address: {sample_address}")
        
        # Generate default letter content
        default_letter = generate_default_letter(auction_details, auction_date, auction_time, sample_address)
        logger.info("Generated default letter content")
        
        # Render template
        logger.info(f"Rendering template with auction_details={auction_details}, auction_date={auction_date}, auction_time={auction_time}")
        return render_template('edit_letter.html', 
                            auction_code=auction_code,
                            sample_address=sample_address,
                            auction_details=auction_details,
                            auction_date=auction_date,
                            auction_time=auction_time,
                            default_letter=default_letter)
    except Exception as e:
        logger.error(f"Error editing letter: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error editing letter: {str(e)}', 'error')
        return redirect(url_for('neighbor_letters_bp.home'))

@neighbor_letters_bp.route('/view-confirmation/<auction_code>')
def view_confirmation(auction_code):
    """View confirmation page with processed addresses"""
    try:
        if 'processed_data' not in session:
            return render_template('error.html', 
                                message='No processed data found. Please upload a CSV file first.')
            
        processed_data = session['processed_data']
        return render_template('confirmation.html', 
                            addresses=processed_data, 
                            auction_code=auction_code)
        
    except Exception as e:
        logger.error(f"Error viewing confirmation: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template('error.html', 
                            message=f'Error viewing confirmation: {str(e)}')

@neighbor_letters_bp.route('/send-letters/<auction_code>', methods=['POST'])
def send_letters(auction_code):
    """Send letters through Lob"""
    try:
        if 'processed_data' not in session:
            return jsonify({
                'success': False,
                'message': 'No processed data found. Please upload a CSV file first.'
            }), 400
            
        processed_data = session['processed_data']
        
        # Send letters through Lob
        letter_generator.send_letters(processed_data, auction_code)
        
        return jsonify({
            'success': True,
            'message': 'Letters sent successfully'
        })
        
    except Exception as e:
        logger.error(f"Error sending letters: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error sending letters: {str(e)}'
        }), 500

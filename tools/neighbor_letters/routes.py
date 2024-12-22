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
    """Generate default letter content with auction details"""
    if not auction_details:
        return "Letter content will be generated when auction details are available."
    
    # Format current date
    current_date = datetime.now().strftime('%B %d, %Y')
    
    # Extract manager info from description if available
    manager_info = {
        'name': '',
        'phone': '',
        'email': ''
    }
    description = auction_details.get('description', '')
    if 'Auction Manager:' in description:
        try:
            manager_section = description.split('Auction Manager:')[1].split('</p>')[0]
            if '@mclemoreauction.com' in manager_section:
                manager_info['email'] = manager_section.split('mailto:')[1].split('"')[0]
            if any(char.isdigit() for char in manager_section):
                # Extract phone number - assuming format like 731-607-0789
                import re
                phone_match = re.search(r'\d{3}[-\s]?\d{3}[-\s]?\d{4}', manager_section)
                if phone_match:
                    manager_info['phone'] = phone_match.group()
            # Extract name - assuming it's between <br/> tags
            name_match = re.search(r'<br/>(.*?)<br/>', manager_section)
            if name_match:
                manager_info['name'] = name_match.group(1).strip()
        except Exception as e:
            logger.error(f"Error extracting manager info: {str(e)}")
    
    # Clean description - remove HTML and manager section
    description = auction_details.get('description', '').split('<p><b>Auction Manager:')[0]
    description = BeautifulSoup(description, 'html.parser').get_text().strip()
    
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

    <p>The auction will take place on our website at <b><a href="https://www.mclemoreauction.com">www.mclemoreauction.com</a></b>. You may register to bid at <b><a href="https://www.mclemoreauction.com/register">www.mclemoreauction.com/register</a></b>.</p>

    <p>Note: <b>This auction closes {bidding_end}.</b></p>

    <p>Please contact <b>{manager_info['name']}</b> at <b>{manager_info['phone']}</b> or <b><a href="mailto:{manager_info['email']}">{manager_info['email']}</a></b> to schedule an appointment to view this property.</p>

    <p><b>Please scan the QR code to visit our website.</b></p>

    <ul class="signature-list">
        <li class="signature-paragraph">
            Yours Truly,<br>
            <img src="https://tools.mclemoreauction.com/static/images/signature.png" alt="Signature" class="signature-image"><br>
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

        # Process the data
        try:
            # Check if it's CRS format
            if all(col in df.columns for col in ['Owner 1', 'Owner Address', 'Owner City', 'Owner State', 'Owner Zip']):
                logger.info("Detected CRS format")
                processed_df = pd.DataFrame({
                    'Name': df['Owner 1'].astype(str),
                    'Address': df['Owner Address'].astype(str),
                    'City': df['Owner City'].astype(str),
                    'State': df['Owner State'].astype(str),
                    'Zip': df['Owner Zip'].astype(str)
                })
            # Check if it's simple format
            elif all(col in df.columns for col in ['Name', 'Address', 'City', 'State', 'Zip']):
                logger.info("Detected simple format")
                processed_df = df[['Name', 'Address', 'City', 'State', 'Zip']].astype(str)
            else:
                logger.error(f"Invalid column format. Found columns: {list(df.columns)}")
                return jsonify({
                    'success': False, 
                    'message': 'Invalid CSV format. Please ensure your file has either:\n' +
                              '1. CRS format: Owner 1, Owner Address, Owner City, Owner State, Owner Zip\n' +
                              '2. Simple format: Name, Address, City, State, Zip'
                }), 400

            # Clean the data
            logger.info("Cleaning data...")
            processed_df = processed_df.dropna()
            processed_df['Name'] = processed_df['Name'].str[:40]  # Truncate names
            processed_df = processed_df.drop_duplicates()  # Remove duplicates
            
            # Convert empty strings to NaN and drop those rows
            processed_df = processed_df.replace(r'^\s*$', pd.NA, regex=True)
            processed_df = processed_df.dropna()

            # Save processed data
            output_dir = os.path.join(current_app.root_path, 'data', auction_code)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'processed_addresses.csv')
            processed_df.to_csv(output_file, index=False)

            logger.info(f"Successfully processed and saved {len(processed_df)} addresses")

            return jsonify({
                'success': True,
                'message': 'File processed successfully',
                'total_rows': len(df),
                'processed_rows': len(processed_df),
                'skipped_rows': len(df) - len(processed_df)
            })

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

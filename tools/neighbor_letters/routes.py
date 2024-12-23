"""Routes for neighbor letters functionality."""
import os
import json
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from csv_processor import CSVProcessor, CSVProcessorError
from utils.lob_utils import LobClient, Address, LobAPIError
from auction_api import AuctionMethodAPI, AuctionNotFoundError

neighbor_letters = Blueprint('neighbor_letters', __name__, url_prefix='/neighbor_letters')

@neighbor_letters.route('/')
def home():
    """
    Show a single page with CSV upload form (in home.html).
    """
    return render_template('neighbor_letters/home.html')

@neighbor_letters.route('/process', methods=['POST'], endpoint='process_csv')
def process_csv_file():
    """
    Handle CSV file + parse + store, then return JSON with stats.
    """
    auction_code = request.form.get('auction_code', '').strip()
    file = request.files.get('file')

    if not file or not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Please upload a .csv file'}), 400
    if not auction_code:
        return jsonify({'success': False, 'message': 'Auction code is required'}), 400

    try:
        df = pd.read_csv(file)
        processor = CSVProcessor()
        result_df, stats = processor.process_csv_data(df)

        data_folder = current_app.config.get('DATA_FOLDER')
        if not data_folder:
            data_folder = os.path.join(os.getcwd(), "data")

        # Ensure data_folder exists
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        out_path = os.path.join(data_folder, f"{auction_code}_processed.csv")
        result_df.to_csv(out_path, index=False)

        return jsonify({
            'success': True,
            'message': 'CSV uploaded and processed successfully.',
            'stats': stats,
            'auction_code': auction_code
        }), 200

    except (CSVProcessorError, ValueError) as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f"Unexpected error: {str(e)}"}), 500

@neighbor_letters.route('/send', methods=['POST'])
def send_letters():
    """
    Send letters using Lob.
    Expects JSON with a "letter_content" and a list of addresses.
    """
    data = request.get_json()
    letter_content = data.get('letter_content', '')
    addresses_data = data.get('addresses', [])

    if not letter_content or not addresses_data:
        return jsonify({'success': False, 'message': 'Missing letter_content or addresses'}), 400

    lob_client = LobClient(use_test_key=True)  # or False, depending on environment

    # Convert address data to Address objects
    address_objects = []
    for addr_dict in addresses_data:
        address_objects.append(
            Address(
                name=addr_dict.get('name', 'Unknown'),
                address_line1=addr_dict.get('address_line1', ''),
                address_city=addr_dict.get('address_city', ''),
                address_state=addr_dict.get('address_state', ''),
                address_zip=addr_dict.get('address_zip', '')
            )
        )

    try:
        batch_result = lob_client.send_batch(address_objects, letter_content)
        return jsonify({'success': True, 'results': batch_result}), 200
    except LobAPIError as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@neighbor_letters.route('/edit/<auction_code>', methods=['GET', 'POST'])
def edit(auction_code):
    """
    Editing a letter for a given auction_code.
    - Fetch Auction data from AuctionMethodAPI
    - Load or create letter_template.html in /data/<auction_code>/
    - Render edit.html with both
    """
    # Attempt to fetch Auction details
    auction_data = None
    try:
        api = AuctionMethodAPI()
        auction_data = api.get_auction_details(auction_code)
        if not auction_data:
            flash(f"Auction {auction_code} not found in AuctionMethod API.", "error")
    except AuctionNotFoundError:
        flash(f"Auction {auction_code} not found in AuctionMethod API.", "error")
    except Exception as ex:
        flash(f"Error fetching auction data: {ex}", "error")
        auction_data = {
            'title': '',
            'location': '',
            'date': '',
            'time': '',
            'description': ''
        }

    data_folder = current_app.config.get('DATA_FOLDER') or os.path.join(os.getcwd(), "data")
    code_folder = os.path.join(data_folder, auction_code)
    os.makedirs(code_folder, exist_ok=True)

    letter_file_path = os.path.join(code_folder, "letter_template.html")

    if request.method == 'POST':
        # Save posted letter content
        posted_content = request.form.get('letter_content', '')
        with open(letter_file_path, 'w', encoding='utf-8') as f:
            f.write(posted_content)
        flash("Letter template saved successfully.", "success")

        return render_template('neighbor_letters/edit.html',
                               auction_code=auction_code,
                               auction=auction_data,
                               letter_content=posted_content)

    # For GET, if letter_file doesn’t exist, create it with a default snippet
    if not os.path.exists(letter_file_path):
        default_content = """<!DOCTYPE html>
        <html>
<head>
    <link href="/static/css/styles.css" rel="stylesheet">
</head>
<body>
    <div class="letter-content ql-editor">
        <p>{{ current_date }}</p>
    <p>RE: Upcoming Auction of <b>{{ auction_title }}</b></p>

    <p>Dear Sir or Madam:</p>

    <p>{{ auction_description }}</p>

    <p>The property address is <b>{{ property_address }}.</b></p>

    <p>Based on our research, you own real estate near the property we are selling.</p>

    <p>The auction will take place on our website at <b><a href="https://www.mclemoreauction.com">www.mclemoreauction.com</a></b>. You may register to bid at <b><a href="https://www.mclemoreauction.com/register">www.mclemoreauction.com/register</a></b>.</p>

    <p>Note: <b>This auction closes {{ bidding_end }}.</b></p>

    <p>Please contact <b>{{ manager_name }}</b> at <b>{{ manager_phone }}</b> or <b><a href="mailto:{{ manager_email }}">{{ manager_email }}</a></b> to schedule an appointment to view this property.</p>

    <p><b>Please scan the QR code to visit our website.</b></p>

    <ul class="signature-list">
        <li class="signature-paragraph">
            Yours Truly,<br>
            <img src="https://tools.mclemoreauction.com/static/images/signature.png" alt="Signature" class="signature-image"><br>
            <b>Will McLemore, CAI</b><br>
            <b><a href="mailto:will@mclemoreauction.com">will@mclemoreauction.com</a> | (615) 636-9602</b>
        </li>
    </ul>
</div>
</body>
</html>
"""
        with open(letter_file_path, 'w', encoding='utf-8') as f:
            f.write(default_content)

    # Read and pass the content to the template
    with open(letter_file_path, 'r', encoding='utf-8') as f:
        existing_content = f.read()

    return render_template('neighbor_letters/edit.html',
                           auction_code=auction_code,
                           auction=auction_data,
                           letter_content=existing_content)
"""Routes for neighbor letters functionality."""
import os
import json
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, current_app
from csv_processor import CSVProcessor, CSVProcessorError
from utils.lob_utils import LobClient, Address, LobAPIError

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
            # fallback to "data" folder in current working directory
            data_folder = os.path.join(os.getcwd(), "data")
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
    Minimal example of editing a letter for a given auction_code
    """
    if request.method == 'POST':
        # Save posted letter content, etc.
        return f"Letter content saved for {auction_code}"
    return f"Editing letter for {auction_code}"
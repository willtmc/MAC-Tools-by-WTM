"""Routes for neighbor letters functionality."""
import os
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from utils.lob_utils import LobClient, Address, LobAPIError

neighbor_letters = Blueprint('neighbor_letters', __name__, url_prefix='/neighbor_letters')

@neighbor_letters.route('/')
def home():
    """
    This is the home endpoint for neighbor letters.
    """
    return render_template('neighbor_letters/home.html')

@neighbor_letters.route('/process', methods=['GET', 'POST'])
def process():
    """
    Page or endpoint for uploading CSV addresses.
    If GET, display the page. If POST, handle the file.
    """
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'message': 'Please upload a .csv file'}), 400
        # In a real scenario, parse CSV here.
        return jsonify({'success': True, 'message': 'CSV uploaded successfully!', 'stats': {}}), 200
    # If GET, render a page that instructs user to upload CSV
    return render_template('neighbor_letters/letters.html')

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

# Example route if you want “edit_letter” style usage:
@neighbor_letters.route('/edit/<auction_code>', methods=['GET', 'POST'])
def edit(auction_code):
    """
    Minimal example of editing a letter for a given auction_code
    """
    if request.method == 'POST':
        # Save posted letter content, etc.
        return f"Letter content saved for {auction_code}"
    return f"Editing letter for {auction_code}"
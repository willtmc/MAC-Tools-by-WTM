from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, \
    send_from_directory, abort
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import qrcode
import os
import hashlib
import hmac
from authlib.integrations.flask_client import OAuth
from authlib.jose import JoseError
import logging
import requests
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz
import secrets
import pandas as pd
import io
import dropbox
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeSerializer
from requests.auth import HTTPBasicAuth
import sqlite3
from dotenv import load_dotenv
import tempfile

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = '__Secure-session'

logging.basicConfig(level=logging.INFO)

central = pytz.timezone('US/Central')

EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

AM_API_KEY = os.getenv('AM_API_KEY')

LOB_API_KEY = os.getenv('LOB_API_KEY')

DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

MEMBER_ID = os.getenv('MEMBER_ID')

dbx_team = dropbox.DropboxTeam(DROPBOX_ACCESS_TOKEN)
dbx_user = dbx_team.as_user(MEMBER_ID)
team_space_root_info = dbx_user.users_get_current_account().root_info
root_namespace_id = team_space_root_info.root_namespace_id
dbx_user_space = dbx_user.with_path_root(dropbox.common.PathRoot.namespace_id(root_namespace_id))

oauth = OAuth(app)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = '/callback'

oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    authorize_params=None,
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri=REDIRECT_URI,
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)


def generate_csrf_token():
    session['csrf_token'] = hmac.new(
        app.config['SECRET_KEY'].encode(),
        str(session.get('user_id', '')).encode(),
        hashlib.sha256
    ).hexdigest()
    return session['csrf_token']


@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token())


@app.before_request
def generate_nonce():
    request.nonce = secrets.token_hex(16)


@app.after_request
def add_security_headers(response):
    nonce = request.nonce
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://cdn.quilljs.com; "
        f"style-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdn.quilljs.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers['Permissions-Policy'] = (
        "geolocation=(), "
        "midi=(), "
        "sync-xhr=(), "
        "microphone=(), "
        "camera=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "fullscreen=(self), "
        "payment=()"
    )
    return response


@app.route('/')
def home():
    if 'google_token' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('home'))


@app.route('/callback')
def authorized():
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token, nonce=token['userinfo']['nonce'])
    except JoseError as e:
        flash('Authentication failed: {}'.format(e), 'error')
        return redirect(url_for('home'))
    except Exception as e:
        flash('An error occurred: {}'.format(e), 'error')
        return redirect(url_for('home'))

    if not user_info:
        flash('Authentication failed.', 'error')
        return redirect(url_for('home'))

    session['google_token'] = token
    session['user'] = user_info

    if user_info['email'].split('@')[1] != 'mclemoreauction.com':
        flash('Access denied: Unauthorized domain', 'error')
        return redirect(url_for('home'))

    return redirect(url_for('index'))


@app.route('/home')
def index():
    if 'google_token' not in session:
        return redirect(url_for('home'))
    return render_template('index.html')


@app.route('/tmp/<filename>')
def serve_temp_file(filename):
    if not os.path.exists(os.path.join("/var/www/flask_app/tmp/", filename)):
        abort(404)
    return send_from_directory("/var/www/flask_app/tmp/", filename)


@app.route('/qrcodegenerator', methods=['GET', 'POST'])
def qrcodegenerator():
    if 'google_token' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        if request.form.get('csrf_token') != session.get('csrf_token'):
            flash('CSRF token missing or incorrect.', 'error')
            return redirect(url_for('qrcodegenerator'))

        auction_code = request.form['auction-code']
        starting_lot = int(request.form['starting-lot'])
        ending_lot = int(request.form['ending-lot'])

        pdf_file_path = "/var/www/flask_app/tmp/qr_code_sheet.pdf"

        c = canvas.Canvas(pdf_file_path, pagesize=letter)

        num_sheets = (ending_lot - starting_lot) // 30 + 1
        for i in range(num_sheets):
            generate_sheet(c, auction_code, starting_lot + i * 30)

        c.save()

        response = send_file(pdf_file_path, as_attachment=True, download_name="auction_labels.pdf")
        response.call_on_close(lambda: os.remove(pdf_file_path))

        return response

    csrf_token = session.get('csrf_token') or generate_csrf_token()
    return render_template('qrcodegenerator.html', csrf_token=csrf_token)


def generate_sheet(c, auction_code, starting_lot):
    page_width, page_height = 612, 792
    label_width = 189
    label_height = 72
    top_bottom_margin = 36
    side_margin = 20
    for row in range(10):
        for col in range(3):
            x_adjustment = 0
            if col == 0:
                x_adjustment = -9
            elif col == 2:
                x_adjustment = 9

            lot_number = starting_lot + row * 3 + col
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=1,
            )
            url = f"https://www.mclemoreauction.com/auction/{auction_code}/lot/{str(lot_number).zfill(4)}"
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").resize((45, 45))

            temp_file = tempfile.NamedTemporaryFile(delete=False)
            qr_img.save(temp_file, 'PNG')

            x = side_margin + col * label_width + x_adjustment + 6
            y = page_height - top_bottom_margin - row * label_height - 58

            c.drawImage(temp_file.name, x + 130, y, 50, 50)
            c.setFont("Helvetica", 27)
            c.drawString(x + 10, y + 15, f"Lot {str(lot_number).zfill(4)}")
            c.setFont("Helvetica", 12)
            c.drawString(x + 10, y - 10, "www.McLemoreAuction.com")

            os.unlink(temp_file.name)

    c.showPage()


@app.route('/neighborlettergenerator', methods=['GET', 'POST'])
def neighborlettergenerator():
    if 'google_token' not in session:
        return redirect(url_for('home'))

    nonce = request.nonce

    if request.method == 'POST':
        received_csrf_token = request.form.get('csrf_token')
        session_csrf_token = session.get('csrf_token')

        app.logger.info(f"Received CSRF Token: {received_csrf_token}")
        app.logger.info(f"Session CSRF Token: {session_csrf_token}")

        if request.form.get('csrf_token') != session.get('csrf_token'):
            flash('CSRF token missing or incorrect.', 'error')
            return redirect(url_for('neighborlettergenerator'))

        auction_code = request.form.get('auction-code')
        if not auction_code:
            flash('Auction code is required.', 'error')
            return redirect(url_for('neighborlettergenerator'))

        session['auction_code'] = auction_code

        url = f'https://www.mclemoreauction.com/uapi/auction/{auction_code}'
        headers = {'X-ApiKey': AM_API_KEY}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            flash('Error fetching auction details.', 'error')
            return redirect(url_for('neighborlettergenerator'))

        auction_data = response.json().get('auction', {})

        current_date = datetime.now(central).strftime('%B %d, %Y')

        auction_title = auction_data.get('title', 'Auction title not found')

        description = auction_data.get('description', 'Description not found')

        property_address = f"{auction_data.get('address', '')}, {auction_data.get('city', '')}, {auction_data.get('state_name', '')} {auction_data.get('zip', '')}"

        epoch_timestamp = int(auction_data.get('ends', 0))
        central_time = adjust_for_dst(epoch_timestamp)
        bidding_end = central_time.strftime('%A, %B %d, %Y, at %I:%M:%S %p') + ' CT'

        manager_name = ''
        manager_phone = ''
        manager_email = ''
        manager_info_pattern = re.compile(
            r'Auction Manager:\s*(?:<br\s*/?>\s*|\s*)*(.*?)<br\s*/?>\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\s*<br\s*/?>\s*<a\s+href="mailto:(.*?)"',
            re.DOTALL
        )
        managers = manager_info_pattern.findall(description)
        if managers:
            manager_name = re.sub(r'<[^>]*>', '', managers[0][0].strip())
            manager_phone = managers[0][1].strip().replace('\n', ' ')
            manager_email = managers[0][2].strip().replace('\n', ' ')

        cleaned_description = clean_description(description).strip()
        soup = BeautifulSoup(cleaned_description, 'html.parser')
        plain_text_description = (soup.get_text(separator=' ').lstrip())

        session['edited_letter_content'] = None

        letter_content = render_template(
            'letter_template.html',
            current_date=current_date,
            auction_title=auction_title,
            auction_description=plain_text_description,
            property_address=property_address,
            bidding_end=bidding_end,
            manager_name=manager_name,
            manager_phone=manager_phone,
            manager_email=manager_email
        )

        edited_letter_content = session.get('edited_letter_content')
        if edited_letter_content:
            letter_content = edited_letter_content

        return render_template('neighborlettergenerator.html', letter_content=letter_content, nonce=nonce)

    csrf_token = session.get('csrf_token') or generate_csrf_token()
    app.logger.info(f"Generated GET CSRF Token: {csrf_token}")
    return render_template('neighborlettergenerator.html', nonce=nonce, csrf_token=csrf_token)


def adjust_for_dst(epoch_timestamp):
    utc_time = datetime.utcfromtimestamp(epoch_timestamp).replace(tzinfo=pytz.utc)

    central_time_naive = utc_time.astimezone(central)

    year = central_time_naive.year
    dst_start = central.localize(datetime(year, 3, 10), is_dst=None).astimezone(pytz.utc)
    dst_end = central.localize(datetime(year, 11, 3), is_dst=None).astimezone(pytz.utc)

    if dst_start <= utc_time < dst_end:
        central_time_naive += timedelta(hours=1)

    return central_time_naive


def clean_description(description):
    description = re.sub(r'Auction Manager:.*?(\(\d{3}\)\s?\d{3}-\d{4}|\d{3}-\d{3}-\d{4}|[\w\.-]+@[\w\.-]+)', '',
                         description, flags=re.DOTALL)
    description = re.sub(r'[\w\.-]+@[\w\.-]+', '', description)
    description = re.sub(r'[^.]*?buyer[’\']s premium[^.]*?\.', '', description, flags=re.DOTALL | re.IGNORECASE)
    description = re.sub(r'<br\s*/?>', '<br>', description)
    description = re.sub(r'\s{2,}', ' ', description)
    description = description.strip()
    return description


@app.route('/save-letter', methods=['POST'])
def save_letter():
    if 'google_token' not in session:
        app.logger.error("Unauthorized access attempt.")
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 401

    try:
        app.logger.info("Receiving JSON data...")
        data = request.get_json()
        csrf_token = data.get('csrf_token')

        if not csrf_token or csrf_token != session.get('csrf_token'):
            app.logger.error("CSRF token mismatch or missing.")
            return jsonify({'success': False, 'message': 'CSRF token missing or incorrect'}), 403

        if not data:
            app.logger.error("Invalid JSON data.")
            return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

        edited_letter_content = data.get('edited_content')
        session['edited_letter_content'] = edited_letter_content

        if not edited_letter_content:
            app.logger.error("No content provided in the request.")
            return jsonify({'success': False, 'message': 'No content provided'}), 400

        template_path = '/var/www/flask_app/static/lob_template.html'
        with open(template_path, 'r') as base_template_file:
            base_template = base_template_file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', dir='/var/www/flask_app/tmp/') as temp_file:
            temp_file_path = temp_file.name
            filled_template = base_template.replace('{{ edited_letter_content }}', edited_letter_content)
            temp_file.write(filled_template.encode('utf-8'))

        session['temp_file_path'] = temp_file_path

        app.logger.info(f"Letter content saved successfully to {temp_file_path}.")
        return jsonify({'success': True,
                        'temp_file_url': url_for('serve_temp_file', filename=os.path.basename(temp_file_path),
                                                 _external=True)})
    except Exception as e:
        app.logger.error(f"Error saving letter content: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while saving the letter content.'}), 500


@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    if 'google_token' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    csrf_token = request.form.get('csrf_token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        app.logger.error("CSRF token mismatch or missing.")
        return jsonify({'success': False, 'message': 'CSRF token missing or incorrect'}), 403

    try:
        auction_code = session.get('auction_code')
        if not auction_code:
            return jsonify({'success': False, 'message': 'Auction code not found.'}), 400

        file = request.files.get('csv-file')
        if not file or not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'message': 'Invalid file format.'}), 400

        processed_data, owner_duplicates_removed, address_duplicates_removed, cemeteries_removed, rows_with_blanks_removed = process_csv_data(
            file, auction_code)

        output = io.BytesIO()
        processed_data.to_csv(output, index=False)
        output.seek(0)

        dropbox_folder = find_dropbox_folder(auction_code)
        if not dropbox_folder:
            return jsonify({'success': False, 'message': f'Folder for auction code {auction_code} not found.'}), 404

        dropbox_file_path = f'{dropbox_folder}/processed-neighbors-{auction_code}.csv'

        try:
            dbx_user_space.files_upload(output.read(), dropbox_file_path, mode=dropbox.files.WriteMode.overwrite)
        except dropbox.exceptions.PathRootError as e:
            app.logger.error(f"PathRootError encountered: {e}")
            return jsonify({'success': False, 'message': 'PathRootError: Check folder permissions and path.'}), 500
        except dropbox.exceptions.ApiError as e:
            app.logger.error(f"API error during file upload: {e}")
            return jsonify({'success': False, 'message': 'Failed to upload file: API error occurred.'}), 500

        try:
            existing_links = dbx_user_space.sharing_list_shared_links(path=dropbox_file_path)
            if existing_links.links:
                dropbox_shared_link = existing_links.links[0].url
            else:
                shared_link_metadata = dbx_user_space.sharing_create_shared_link_with_settings(dropbox_file_path)
                dropbox_shared_link = shared_link_metadata.url
        except dropbox.exceptions.ApiError as e:
            app.logger.error(f"Error creating or retrieving shared link: {e}")
            return jsonify({'success': False, 'message': f'Failed to create or retrieve shared link: {str(e)}'}), 500

        return jsonify({
            'success': True,
            'dropbox_link': dropbox_shared_link,
            'owner_duplicates_removed': owner_duplicates_removed,
            'address_duplicates_removed': address_duplicates_removed,
            'cemeteries_removed': cemeteries_removed,
            'rows_with_blanks_removed': rows_with_blanks_removed
        })

    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500


def find_dropbox_folder(auction_code):
    try:
        cursor = None
        target_prefix = auction_code[:4]

        while True:
            result = dbx_user_space.files_list_folder_continue(cursor) if cursor else dbx_user_space.files_list_folder(
                '/MAC Auctions/')
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FolderMetadata) and entry.name.startswith(target_prefix):
                    return entry.path_lower

            if not result.has_more:
                break
            cursor = result.cursor

        app.logger.warning(f"No folder found for auction code {auction_code}")
        return None

    except dropbox.exceptions.ApiError as e:
        app.logger.error(f"Error listing Dropbox folders: {e}")
        return None


def process_csv_data(file, auction_code):
    try:
        # Read the CSV file
        csv_data = pd.read_csv(io.StringIO(file.stream.read().decode('utf-8')))
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {str(e)}")

    try:
        # Define the expected headers
        expected_columns = ['Name', 'Address', 'City', 'State', 'Zip']
        columns_to_keep = {col: None for col in expected_columns}

        # Check for and map existing columns (case-insensitive matching)
        for col_name in csv_data.columns:
            lower_col_name = col_name.lower()  # Normalize to lowercase for case-insensitive matching
            for expected_col in expected_columns:
                if expected_col.lower() in lower_col_name and columns_to_keep[expected_col] is None:
                    columns_to_keep[expected_col] = col_name

        # Identify missing columns and add them with default empty values
        for key, value in columns_to_keep.items():
            if value is None:
                columns_to_keep[key] = key
                csv_data[key] = ""  # Add missing column with empty values

        # Extract the relevant columns into a new DataFrame
        processed_data = csv_data[list(columns_to_keep.values())]

    except Exception as e:
        raise ValueError(f"Error selecting columns: {str(e)}")

    try:
        initial_count = len(processed_data)
        processed_data = processed_data.drop_duplicates(subset=columns_to_keep['Name'])
        owner_duplicates_removed = initial_count - len(processed_data)

        initial_count = len(processed_data)
        processed_data = processed_data.drop_duplicates(subset=columns_to_keep['Address'])
        address_duplicates_removed = initial_count - len(processed_data)

        initial_count = len(processed_data)
        processed_data = processed_data[~processed_data[columns_to_keep['Name']].str.contains('cemetery', case=False, na=False)]
        cemeteries_removed = initial_count - len(processed_data)

        initial_count = len(processed_data)
        processed_data = processed_data.dropna()
        rows_with_blanks_removed = initial_count - len(processed_data)

        def truncate_name(name, max_length=40):
            abbreviations = {
                "United States Of America": "US",
                'Revocable Living Trust': 'Rev. Trust',
                'C/O': '',
                'and': '&',
                'The ': '',
                'Etux': '',
                'Etvir': '',
                'National Park Service': 'Nat. Park Serv.',
                'Irrevocable Trust': 'Irrev. Trust',
                'Company': 'Co.',
                'Incorporated': 'Inc.',
                'Church': 'Ch.',
                'Corporation': 'Corp.',
                'Living Trust': 'Lv. Trust'
            }

            for phrase, abbreviation in abbreviations.items():
                name = name.replace(phrase, abbreviation)

            return name[:max_length] if len(name) > max_length else name

        processed_data[columns_to_keep['Name']] = processed_data[columns_to_keep['Name']].apply(truncate_name)

        processed_data = processed_data[[columns_to_keep['Name'],
                                         columns_to_keep['Address'],
                                         columns_to_keep['City'],
                                         columns_to_keep['State'],
                                         columns_to_keep['Zip']]]

    except Exception as e:
        raise ValueError(f"Error processing data: {str(e)}")

    return processed_data, owner_duplicates_removed, address_duplicates_removed, cemeteries_removed, rows_with_blanks_removed



def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_FROM, EMAIL_TO, text)
        server.quit()
        app.logger.info(f"Email sent to {EMAIL_TO}")
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")


@app.route('/redirect/<auction_code>')
def track_qr(auction_code):
    redirect_url = f"https://www.mclemoreauction.com/auction/{auction_code}"

    try:
        conn = sqlite3.connect('qr_tracking.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO qr_scans (auction_code, scan_date) VALUES (?, ?)",
                       (auction_code, datetime.utcnow()))
        conn.commit()
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {str(e)}")
    finally:
        conn.close()

    return redirect(redirect_url, code=302)


def retrieve_processed_data(auction_code):
    dropbox_folder = find_dropbox_folder(auction_code)
    if not dropbox_folder:
        app.logger.warning(f"Folder for auction code {auction_code} not found.")
        return None

    dropbox_file_path = f'{dropbox_folder}/processed-neighbors-{auction_code}.csv'

    try:
        metadata, res = dbx_user_space.files_download(dropbox_file_path)
        file_content = res.content

        processed_data = pd.read_csv(io.BytesIO(file_content))
        return processed_data

    except dropbox.exceptions.ApiError as e:
        app.logger.error(f"Failed to download file from Dropbox: {e}")
        return None


@app.route('/send-confirmation-email', methods=['POST'])
def process_and_send_letters():
    if 'google_token' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    data = request.get_json()
    csrf_token = data.get('csrf_token')

    if not csrf_token or csrf_token != session.get('csrf_token'):
        app.logger.error("CSRF token mismatch or missing.")
        return jsonify({'success': False, 'message': 'CSRF token missing or incorrect'}), 403

    try:
        auction_code = session.get('auction_code')
        if not auction_code:
            return jsonify({'success': False, 'message': 'Auction code not found.'}), 400

        processed_data = retrieve_processed_data(auction_code)
        if processed_data is None:
            return jsonify({'success': False, 'message': 'Processed data not found or failed to retrieve.'}), 500

        letter_content = session.get('edited_letter_content')
        if not letter_content:
            return jsonify({'success': False, 'message': 'Letter content not found.'}), 400

        total_recipients = len(processed_data)

        cost_per_letter = 1.14
        total_cost = total_recipients * cost_per_letter * 1.0021

        view_link = url_for('view_confirmation', auction_code=auction_code, _external=True)
        confirm_link = generate_secure_link(auction_code)

        email_body = (
            f"Confirmation Details:\n\n"
            f"Total Recipients: {total_recipients}\n"
            f"Estimated Total Cost: ${total_cost:.2f}\n\n"
            f"**View the letter content before sending**:\n{view_link}\n\n"
            f"**Confirm and send the letters**:\n{confirm_link}\n\n"
            "Please review the details above and confirm if you would like to proceed with sending the letters."
        )

        send_email("Confirmation for Neighbor Letters", email_body)

        return jsonify({'success': True, 'message': 'Confirmation email sent with review and confirmation links.'})
    except Exception as e:
        app.logger.error(f"Unexpected error during processing: {e}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500


@app.route('/view-confirmation/<string:auction_code>')
def view_confirmation(auction_code):
    try:
        letter_content = session.get('edited_letter_content')
        if not letter_content:
            return "Letter content not found.", 404

        nonce = request.nonce

        html_content = render_template('view_confirmation.html', nonce=nonce, letter_content=letter_content)
        return html_content
    except Exception as e:
        app.logger.error(f"Error generating confirmation view: {e}")
        return "An error occurred.", 500


def generate_secure_link(auction_code):
    serializer = URLSafeSerializer(app.secret_key)
    token = serializer.dumps(auction_code)

    secure_link = url_for('confirm_send', token=token, _external=True)
    return secure_link


@app.route('/confirm-send/<token>', methods=['GET', 'POST'])
def confirm_send(token):
    if 'google_token' not in session:
        app.logger.error("Unauthorized access attempt.")
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 401

    serializer = URLSafeSerializer(app.secret_key)
    try:
        auction_code = serializer.loads(token)
    except Exception as e:
        app.logger.error(f"Invalid or expired token: {e}")
        return jsonify({'success': False, 'message': 'Invalid or expired token.'}), 400

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            app.logger.error("CSRF token mismatch or missing.")
            return jsonify({'success': False, 'message': 'CSRF token missing or incorrect'}), 403

        action = request.form.get('action')

        if action == 'create_campaign':
            try:
                campaign_id = create_campaign(auction_code)
                session['campaign_id'] = campaign_id
                app.logger.info(f'campaign_id: {campaign_id}')

                create_creative(campaign_id, auction_code)
                upload_id = create_upload(campaign_id, auction_code)
                if not upload_id:
                    return jsonify({'success': False, 'message': 'Failed to create upload.'}), 500

                return jsonify({'success': True, 'message': 'Campaign created successfully.'})
            except Exception as e:
                app.logger.error(f"Error creating campaign: {e}")
                return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

        elif action == 'send_campaign':
            try:
                campaign_id = session.get('campaign_id')
                if not campaign_id:
                    return jsonify({'success': False, 'message': 'Campaign ID not found. Please create the campaign first.'}), 400

                send_campaign(campaign_id)
                return jsonify({'success': True, 'message': 'Campaign sent successfully.'})
            except Exception as e:
                app.logger.error(f"Error sending campaign: {e}")
                return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

    nonce = request.nonce
    csrf_token = generate_csrf_token()
    return render_template('confirm_send.html', auction_code=auction_code, csrf_token=csrf_token, nonce=nonce)


def create_campaign(auction_code):
    url = "https://api.lob.com/v1/campaigns"

    payload = {
        "name": f"Test Auction {auction_code} Neighbor Letters",
        "schedule_type": "immediate",
        "use_type": "marketing",
        "metadata": {"auction_code": auction_code},
        "cancel_window_campaign_minutes": 240,
    }
    auth = HTTPBasicAuth(LOB_API_KEY, '')
    response = requests.post(url, json=payload, auth=auth)

    if response.status_code == 200:
        campaign_data = response.json()
        return campaign_data['id']
    else:
        raise Exception(f"Failed to create campaign: {response.text}")


def create_creative(campaign_id, auction_code):
    tmpl_id = None
    auth = HTTPBasicAuth(LOB_API_KEY, '')
    try:
        processed_data = retrieve_processed_data(auction_code)
        if processed_data is None:
            raise ValueError(f"No data found for auction code {auction_code}")

        temp_file_path = session.get('temp_file_path')
        app.logger.info(f"temp_file_path: {temp_file_path}")
        if not temp_file_path:
            raise ValueError("No temporary file path found in session.")

        with open(temp_file_path, 'r') as file:
            html_content = file.read()

        tmpl_url = "https://api.lob.com/v1/templates"

        payload = {
            "html": html_content,
            "description": f"Auction {auction_code} Template",
            "metadata": {
                "auction_code": auction_code
            }
        }

        response = requests.post(tmpl_url, json=payload, auth=auth)

        if response.status_code == 200:
            template_data = response.json()
            tmpl_id = template_data['id']
            app.logger.info(f"Successfully created template with ID {tmpl_id}")
        else:
            app.logger.error(f"Failed to create template: {response.text}")
            return None

        url = "https://api.lob.com/v1/creatives"

        qr_code_redirect_url = f"https://tools.mclemoreauction.com/redirect/{auction_code}"

        payload = {
            "file": tmpl_id,
            "from": "adr_f0d73795eaaf237a",
            "campaign_id": campaign_id,
            "resource_type": "letter",
            "details": {
                "color": True,
                "address_placement": "top_first_page",
                "double_sided": False,
                "mail_type": "usps_first_class",
                "qr_code": {
                    "position": "relative",
                    "bottom": "0.42",
                    "right": "0.42",
                    "width": "1.75",
                    "redirect_url": qr_code_redirect_url
                }
            },
            "metadata": {
                "auction_code": auction_code
            }
        }

        response = requests.post(url, json=payload, auth=auth)

        if response.status_code != 200:
            app.logger.error(f"Failed to create creative: {response.text}")
        else:
            creative_data = response.json()
            app.logger.info(f"Successfully created creative with ID {creative_data['id']}")

    except Exception as e:
        app.logger.error(f"Error in create_creative: {str(e)}")
        raise

    # finally:
    #     if tmpl_id:
    #         delete_url = f"https://api.lob.com/v1/templates/{tmpl_id}"
    #         delete_response = requests.delete(delete_url, auth=auth)
    #         if delete_response.status_code == 200:
    #             app.logger.info(f"Successfully deleted template with ID {tmpl_id}")
    #         else:
    #             app.logger.error(f"Failed to delete template with ID {tmpl_id}: {delete_response.text}")


def create_upload(campaign_id, auction_code):
    try:
        url = "https://api.lob.com/v1/uploads"
        auth = HTTPBasicAuth(LOB_API_KEY, '')

        required_address_mapping = {
            "name": "Name",
            "address_line1": "Address",
            "address_city": "City",
            "address_state": "State",
            "address_zip": "Zip"
        }

        payload = {
            "campaignId": campaign_id,
            "requiredAddressColumnMapping": required_address_mapping,
        }

        response = requests.post(url, json=payload, auth=auth)
        if response.status_code != 201:
            app.logger.error(f"Failed to create upload: {response.text}")
            return None

        upload_data = response.json()
        upload_id = upload_data['id']

        app.logger.info(f"Successfully created upload with ID {upload_id}")

        temp_csv_path = "/var/www/flask_app/tmp/lob_upload_temp.csv"
        processed_data = retrieve_processed_data(auction_code)
        processed_data.to_csv(temp_csv_path, index=False, encoding='utf-8')

        if not upload_file(upload_id, temp_csv_path):
            return None

        return upload_id

    except Exception as e:
        app.logger.error(f"Error in create_upload: {str(e)}")
        raise


def upload_file(upload_id, temp_csv_path):
    try:
        upload_url = f"https://api.lob.com/v1/uploads/{upload_id}/file"
        auth = HTTPBasicAuth(LOB_API_KEY, '')

        with open(temp_csv_path, 'rb') as f:
            files = {'file': ('lob_upload_temp.csv', f, 'text/csv')}
            response = requests.post(upload_url, files=files, auth=auth)

        if response.status_code != 202:
            app.logger.error(f"Failed to upload file: {response.text}")
            return False

        app.logger.info(f"Successfully uploaded file for upload ID {upload_id}")
        return True

    except Exception as e:
        app.logger.error(f"Error in upload_file: {str(e)}")
        raise


def send_campaign(campaign_id):
    try:
        send_url = f"https://api.lob.com/v1/campaigns/{campaign_id}/send"
        auth = HTTPBasicAuth(LOB_API_KEY, '')

        response = requests.post(send_url, auth=auth)

        if response.status_code != 200:
            app.logger.error(f"Failed to send campaign: {response.status_code} - {response.text}")
            return False

        app.logger.info(f"Successfully sent campaign with ID {campaign_id}")
        return True

    except Exception as e:
        app.logger.error(f"Error in send_campaign: {str(e)}")
        raise


@app.route('/view/')
def view_auction():
    url = f'https://api.lob.com/v1/campaigns'

    auth = HTTPBasicAuth(LOB_API_KEY, '')

    app.logger.info(f"Making request to URL: {url}")

    response = requests.get(url, auth=auth)

    if response.status_code != 200:
        app.logger.error(f"Error fetching campaign details: {response.status_code}")
        return f"Error fetching campaign details: {response.status_code}", 500

    campaign_data = response.json()
    return campaign_data


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

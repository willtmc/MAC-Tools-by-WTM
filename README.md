# McLemore Auction Tools

A Flask-based web application for McLemore Auction Company that provides tools for generating neighbor letters and auction QR codes.

## Features

### 1. Neighbor Letter Generator
- Fetches auction details from McLemore Auction API
- Generates customized letters for property neighbors
- Supports CSV upload for batch processing of neighbor addresses
- Includes duplicate address detection and removal
- Integrates with Lob for mail delivery
- Dropbox integration for storing processed files

### 2. QR Code Generator
- Creates QR codes for auction lots
- Generates printable label sheets
- Supports batch generation for multiple lots

## Setup

### Prerequisites
- Python 3.12+
- Nginx
- Virtual environment
- Access to McLemore Auction API
- Lob API account
- Google OAuth credentials
- Dropbox API access

### Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd mclemore-auction-tools
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your values
```

### Required Environment Variables

- `SECRET_KEY`: Flask secret key
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `AM_API_KEY`: McLemore Auction API key
- `LOB_API_KEY`: Lob API key
- `DROPBOX_ACCESS_TOKEN`: Dropbox access token
- `MEMBER_ID`: Dropbox team member ID
- `EMAIL_FROM`: Sender email for notifications
- `EMAIL_TO`: Recipient email for notifications
- `SMTP_USERNAME`: SMTP username for email
- `SMTP_PASSWORD`: SMTP password for email

## Development

### Local Development
1. Activate virtual environment:
```bash
source venv/bin/activate
```

2. Run Flask development server:
```bash
flask run --debug
```

### Making Changes
1. Create a new branch for your feature:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes
3. Test thoroughly
4. Commit changes:
```bash
git add .
git commit -m "Description of changes"
```

5. Push to GitHub:
```bash
git push origin feature/your-feature-name
```

## Deployment

### Server Requirements
- Ubuntu 22.04 LTS
- Python 3.12+
- Nginx
- Gunicorn

### Deployment Steps
1. Pull latest changes on server:
```bash
cd /var/www/flask_app
git pull origin main
```

2. Update dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

3. Restart services:
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## File Structure
```
/var/www/flask_app/
├── app.py              # Main Flask application
├── daily_report.py     # Daily reporting script
├── dbx_token_refresh.py # Dropbox token refresh script
├── monitor.py          # System monitoring script
├── requirements.txt    # Python dependencies
├── static/            # Static files (CSS, JS, images)
├── templates/         # HTML templates
├── tmp/              # Temporary files (gitignored)
└── venv/             # Virtual environment (gitignored)
```

## Security Notes
- All sensitive credentials should be stored in .env file
- .env file should never be committed to Git
- Google authentication is required for access
- Only mclemoreauction.com email addresses are allowed by default

## Maintenance
- Monitor Dropbox token refresh script
- Check daily reports
- Review system monitoring alerts
- Keep dependencies updated
- Regularly backup database

## Support
Contact Will McLemore for access and permissions.

import sqlite3
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Email variables
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_email(subject, body):
    """
    Sends out email with the given subject and body using the configured SMTP server.
    """
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
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def send_daily_report():
    """
    Generates and sends a daily report of QR code scans.
    It checks the database for new scans since the start of the day,
    compares with previous scan counts, and sends an email if new scans are found.
    """
    logger.info("Executing send_daily_report function")

    try:
        with sqlite3.connect('qr_tracking.db') as conn:
            cursor = conn.cursor()
            start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            cursor.execute('''
                SELECT auction_code, COUNT(*) as scan_count 
                FROM qr_scans 
                WHERE scan_date >= ? 
                GROUP BY auction_code
            ''', (start_of_day,))

            results = cursor.fetchall()

            cursor.execute('SELECT auction_code, last_scan_count FROM last_reports')
            last_report_data = {row[0]: row[1] for row in cursor.fetchall()}

            email_body = "Daily QR Code Scan Report:\n\n"
            has_new_scans = False

            for auction_code, scan_count in results:
                last_scan_count = last_report_data.get(auction_code, 0)

                if scan_count > last_scan_count:
                    has_new_scans = True
                    email_body += f"Auction Code: {auction_code}, New Scans: {scan_count - last_scan_count}\n"

                    cursor.execute('''
                        INSERT INTO last_reports (auction_code, last_scan_count) 
                        VALUES (?, ?)
                        ON CONFLICT(auction_code) DO UPDATE SET last_scan_count=excluded.last_scan_count
                    ''', (auction_code, scan_count))

        if has_new_scans:
            logger.info("New scans detected, sending email")
            send_email('Daily QR Code Scan Report', email_body)
        else:
            logger.info("No new QR scans to report today.")
    except sqlite3.DatabaseError as e:
        logger.error(f"Database error: {e}")


def start_scheduler():
    """
    Starts the scheduler to run the send_daily_report function daily at 12:01 AM CST.
    """
    logger.info("Scheduler started")
    scheduler = BackgroundScheduler()
    central = timezone('America/Chicago')
    scheduler.add_job(send_daily_report, 'cron', hour=0, minute=1, timezone=central)
    scheduler.start()

    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shut down.")


# Initializes the scheduler
if __name__ == "__main__":
    start_scheduler()

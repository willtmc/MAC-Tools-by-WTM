import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import time
import os

URL = "https://tools.mclemoreauction.com"
CHECK_INTERVAL = 3600
EMAIL_FROM = "mclemoreauctiontools@gmail.com"
EMAIL_TO = "ely@mclemoreauction.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')


def send_email(body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = "Website Down Alert"

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_FROM, EMAIL_TO, text)
        server.quit()
        print(f"Email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"Failed to send email: {e}")


def check_website():
    try:
        response = requests.get(URL)
        if response.status_code != 200:
            send_email(f"Website {URL} is down. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        send_email(f"Website {URL} is down. Error: {e}")


if __name__ == '__main__':
    while True:
        check_website()
        time.sleep(CHECK_INTERVAL)
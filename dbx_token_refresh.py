import time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app_key = os.getenv('DBX_APP_KEY')
app_secret = os.getenv('DBX_APP_SECRET')
refresh_token = os.getenv('DBX_REFRESH_TOKEN')


def refresh_dropbox_token(app_key, app_secret, refresh_token):
    token_url = "https://api.dropbox.com/oauth2/token"

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    auth = HTTPBasicAuth(app_key, app_secret)

    response = requests.post(token_url, data=data, auth=auth)

    if response.status_code == 200:
        token_info = response.json()
        new_access_token = token_info['access_token']

        with open("/var/www/flask_app/dropbox_token.env", "w") as token_file:
            token_file.write(f'DROPBOX_ACCESS_TOKEN="{new_access_token}"\n')

            os.environ['DROPBOX_ACCESS_TOKEN'] = new_access_token

        return new_access_token
    else:
        logger.error(f"Failed to refresh token: {response.status_code}")
        return None


while True:
    refresh_dropbox_token(app_key, app_secret, refresh_token)
    logger.info("Refreshing the Dropbox Token")
    time.sleep(14400)

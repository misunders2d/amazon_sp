from sp_api.api import  Reports

import os
from dotenv import load_dotenv
load_dotenv()


REFRESH_TOKEN_EU=os.environ['REFRESH_TOKEN_EU']
REFRESH_TOKEN_US=os.environ['REFRESH_TOKEN_US']

credentials = dict(
    refresh_token=REFRESH_TOKEN_US,
    lwa_app_id=os.environ['CLIENT_ID'],
    lwa_client_secret=os.environ['CLIENT_SECRET']
)

report = Reports(credentials=credentials)
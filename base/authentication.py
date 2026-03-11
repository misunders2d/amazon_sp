import os

import requests
from dotenv import load_dotenv
from sp_api.asyncio.api import Reports

load_dotenv()

REFRESH_TOKEN_EU = os.environ["REFRESH_TOKEN_EU"]
REFRESH_TOKEN_US = os.environ["REFRESH_TOKEN_US"]

credentials = dict(
    refresh_token=REFRESH_TOKEN_US,
    lwa_app_id=os.environ["CLIENT_ID"],
    lwa_client_secret=os.environ["CLIENT_SECRET"],
)


def get_access_token():
    LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": credentials["refresh_token"],
        "client_id": credentials["lwa_app_id"],
        "client_secret": credentials["lwa_client_secret"],
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}

    try:
        lwa_response = requests.post(LWA_TOKEN_URL, data=payload, headers=headers)
        lwa_response.raise_for_status()  # Raise an exception for HTTP errors

        lwa_data = lwa_response.json()
        access_token = lwa_data.get("access_token")
        expires_in = lwa_data.get("expires_in")  # Typically 3600 seconds (1 hour)

        if access_token:
            print(
                f"Successfully obtained LWA Access Token. Expires in {expires_in} seconds."
            )
            return access_token
        else:
            print("Failed to get LWA Access Token from response.")

    except requests.exceptions.RequestException as e:
        print(f"Error exchanging refresh token for LWA Access Token: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"LWA Response error: {e.response.text}")


def get_reports_class():
    return Reports(credentials=credentials)

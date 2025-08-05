from datetime import datetime, timedelta
from sp_api.base import ReportType, ApiResponse
from sp_api.api import CatalogItems
import requests

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

catalog_items = CatalogItems(credentials=credentials)

c2 = catalog_items.get_catalog_item(
    asin="B01M16WBW1",
    includedData=[
        "attributes","summaries","identifiers"#"classifications"#,"dimensions",,
        #"images","productTypes","salesRanks","relationships"#,"vendorDetails"
        ]
    )


from authentication import get_access_token
access_token = get_access_token()
        
url = "https://sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items/B01M16WBW1"

headers = {
    "accept": "application/json",
    "x-amz-access-token":access_token
    }

query_params = {
    "includedData":["attributes","classifications","dimensions","identifiers","images","productTypes","salesRanks","summaries","relationships","vendorDetails"],
    "marketplaceIds":"ATVPDKIKX0DER"
    }
response = requests.get(url, headers=headers, params=query_params)

print(response.text)

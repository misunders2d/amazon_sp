from sp_api.api import ListingsItems, ProductTypeDefinitions

from sp_api.base import SellingApiException, SellingApiServerException, ApiResponse

import os
import time


from dotenv import load_dotenv
from typing import Literal, List

load_dotenv()
MARKETPLACE_IDS = ["ATVPDKIKX0DER", "A2EUQ1WTGCTBG2"]
SELLER_ID = os.environ["SELLER_ID"]

credentials = dict(
    refresh_token=os.environ["REFRESH_TOKEN_US"],
    lwa_app_id=os.environ["CLIENT_ID"],
    lwa_client_secret=os.environ["CLIENT_SECRET"],
)


listings_client = ListingsItems(credentials=credentials)
product_type_client = ProductTypeDefinitions(credentials=credentials)


def get_listing_details(
    sku: str,
    include: List[
        Literal[
            "summaries",
            "attributes",
            "issues",
            "offers",
            "fulfillmentAvailability",
            "procurement",
            "relationships",
            "productTypes",
        ]
    ],
):
    try:
        response = listings_client.get_listings_item(
            sellerId=SELLER_ID, sku=sku, includedData=include
        )
    except (SellingApiException, SellingApiServerException) as e:
        return e
    return response


def get_product_schema(product_type):
    response = product_type_client.get_definitions_product_type(product_type)
    return response.payload["schema"]["link"]["resource"]


def update_listing(sku, patch_body):
    try:
        response = listings_client.patch_listings_item(
            sellerId=SELLER_ID, sku=sku, marketplaceIds=MARKETPLACE_IDS, body=patch_body
        )
        print(f"Updated listing for {sku} with status {response.payload['status']}")
    except SellingApiException as e:
        print(f"Error updating listing for {sku}: {e}")
    except Exception as e:
        print(f"FAILED to update listing for {sku}:\n{e}")


def remove_b2b_price(sku, product_type):
    current_listing = get_listing_details(sku=sku, include=["attributes"])
    if isinstance(current_listing, ApiResponse):
        purchasable_offers = current_listing.payload.get("attributes", {}).get(
            "purchasable_offer", []
        )

        b2b_offers_only = [
            offer
            for offer in purchasable_offers
            if "quantity_discount_plan" in offer or offer["audience"] == "B2B"
        ]

        if b2b_offers_only:
            patch_payload_remove_b2b = {
                "productType": product_type,
                "patches": [
                    {
                        "op": "delete",
                        "path": "/attributes/purchasable_offer",
                        "value": b2b_offers_only,
                    }
                ],
            }
            update_listing(sku, patch_payload_remove_b2b)


def close_listing(sku, product_type):
    current_listing = get_listing_details(sku=sku, include=["attributes"])
    if isinstance(current_listing, ApiResponse):
        fulfillment_availability = current_listing.payload.get("attributes", {}).get(
            "fulfillment_availability", []
        )
        if fulfillment_availability:
            patch_payload_close_listing = {
                "productType": product_type,
                "patches": [
                    {
                        "op": "replace",
                        "path": "/attributes/skip_offer",
                        "value": [{"value": "Yes"}],
                    },
                    {
                        "op": "delete",
                        "path": "/attributes/fulfillment_availability",
                        "value": fulfillment_availability,
                    },
                ],
            }
            update_listing(sku, patch_payload_close_listing)


def batch_delete_listings(skus):
    confirmation = input(
        f'You are about to delete {len(skus)} listings, please confirm by typing "Yes": '
    )
    if confirmation != "Yes":
        print("Exiting...")
        return
    error_skus = {}
    start = time.perf_counter()
    for i, sku in enumerate(skus, start=1):
        print(f"Deleting sku {i} of {len(skus)}")
        try:
            response = listings_client.delete_listings_item(
                sellerId=SELLER_ID,
                sku=sku,
                marketplaceIds=MARKETPLACE_IDS,
            )
            time.sleep(1 / 5)
            print(response.payload["status"])

        except (SellingApiException, SellingApiServerException) as e:
            error = e.error[0]["code"]
            print(f"Error for {sku}: {error}")
            if error in error_skus:
                error_skus[error].append(sku)
            else:
                error_skus[error] = [sku]

    print(f"Job done in {time.perf_counter()-start} seconds")
    return error_skus


def batch_close_listings(skus):
    error_skus = {}
    start = time.perf_counter()
    for i, sku in enumerate(skus, start=1):
        print(f"Checking sku {i} of {len(skus)}")
        response = get_listing_details(
            sku=sku, include=["productTypes", "fulfillmentAvailability"]
        )
        time.sleep(1 / 5)
        if not response.error and isinstance(response, ApiResponse):
            payload = response.payload
            if (
                payload["productTypes"]
                and payload["fulfillmentAvailability"]
                and "fulfillmentChannelCode" in payload["fulfillmentAvailability"][0]
                and payload["fulfillmentAvailability"][0]["fulfillmentChannelCode"]
                == "AMAZON_NA"
            ):
                product_type = payload["productTypes"][0]["productType"]
                close_listing(sku, product_type)
                time.sleep(1 / 5)
            else:
                print(f"{sku} already FBM, skipping")
        elif response.error:
            error = response.error[0]["code"]
            print(f"Error for {sku}: {error}")
            if error in error_skus:
                error_skus[error].append(sku)
            else:
                error_skus[error] = [sku]
        else:
            print(f"Unknown error for {sku}, skipping")

    print(f"Job done in {time.perf_counter()-start} seconds")
    return error_skus


def batch_remove_thread_count(skus):
    product_type_response = get_listing_details(sku=skus[0], include=["productTypes"])
    if isinstance(product_type_response, ApiResponse):
        product_type = product_type_response.payload["productTypes"][0]["productType"]
        patch_body = {
            "productType": product_type,
            "patches": [
                {
                    "op": "delete",
                    "path": "/attributes/thread",
                    # "value": [{'count': [{'value': 0}], 'marketplace_id': 'ATVPDKIKX0DER'}],
                    "value": [{"marketplace_id": "ATVPDKIKX0DER"}],
                },
            ],
        }
        for sku in skus:
            update_listing(sku, patch_body)
            time.sleep(1 / 5)


skus = input("Enter a list of SKUs:\n").split("\n")
print(f"Starting to process {len(skus)} skus")
result = batch_remove_thread_count(skus)

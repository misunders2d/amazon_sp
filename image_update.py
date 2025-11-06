from sp_api.api import ListingsItems
import os, sys, time

from telegram_notifier import send_telegram_message

from image_links import product_details

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

    response = listings_client.get_listings_item(
        sellerId=SELLER_ID, sku=sku, includedData=include
    )
    return response


def update_image(
    sku,
    product_type,
    image_path,
    op: Literal["replace", "delete"] = "replace",
    attribute_path: Literal[
        "main_product_image_locator",
        "other_product_image_locator_1",
        "other_product_image_locator_2",
        "other_product_image_locator_3",
        "other_product_image_locator_4",
        "other_product_image_locator_5",
        "other_product_image_locator_6",
        "other_product_image_locator_7",
        "other_product_image_locator_8",
        "swatch_product_image_locator",
    ] = "main_product_image_locator",
):

    patch_body = {
        "productType": product_type,
        "patches": [
            {
                "op": op,
                "path": f"/attributes/{attribute_path}",  # other_product_image_locator_8
                "value": [{"media_location": image_path}],
            }
        ],
    }
    try:
        response = listings_client.patch_listings_item(
            sellerId=SELLER_ID, sku=sku, marketplaceIds=MARKETPLACE_IDS, body=patch_body
        )
        print(
            f"Image updated for {sku} with status {response.payload['status']}\nImage: {image_path}\n\n"
        )
    except Exception as e:
        print(f"FAILED to update image for {sku}:\n{e}")
        return e


def batch_delete_image(
    SKUS,
    product_type,
    image_path,
    op="delete",
    attribute_path="other_product_image_locator_8",
):
    failed_images = {}
    for sku in SKUS:
        result = update_image(
            sku, product_type, image_path, op="delete", attribute_path=attribute_path
        )
        time.sleep(1 / 5)
        if result:
            failed_images[sku] = result
    return failed_images


if __name__ == "__main__":
    args = sys.argv[1:]
    send_telegram_message(f"Starting cron job with argument {sys.argv[1:]}")

    for product in product_details:
        SKUS = product["skus"]
        image = product["STANDARD_IMAGE"]
        if len(args) > 0 and args[0] == "1":
            image = product["MORNING_IMAGE"]
        elif len(args) > 0 and args[0] == "2":
            image = product["EVENING_IMAGE"]
        product_type = get_listing_details(
            sku=SKUS[0], include=["summaries", "productTypes"]
        ).payload["summaries"][0]["productType"]
        for sku in SKUS:
            update_image(sku, product_type=product_type, image_path=image)
            time.sleep(0.5)

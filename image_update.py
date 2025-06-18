from sp_api.api import ListingsItems
import os, sys, time

from telegram_notifier import send_telegram_message

from image_links import product_details

from dotenv import load_dotenv
load_dotenv()
MARKETPLACE_IDS=["ATVPDKIKX0DER","A2EUQ1WTGCTBG2"]
SELLER_ID=os.environ['SELLER_ID']

credentials = dict(
    refresh_token=os.environ['REFRESH_TOKEN_US'],
    lwa_app_id=os.environ['CLIENT_ID'],
    lwa_client_secret=os.environ['CLIENT_SECRET']
)

listings_client = ListingsItems(credentials=credentials)


MORNING_IMAGE="https://ik.imagekit.io/jgp5dmcfb/Day-night/morning.png"#"https://ik.imagekit.io/jgp5dmcfb/Day-night/4pc_Light%20Gray_Daytime.png"
EVENING_IMAGE="https://ik.imagekit.io/jgp5dmcfb/Day-night/evening.png?updatedAt=1750239337952"#"https://ik.imagekit.io/jgp5dmcfb/Day-night/4pc_Light%20Gray_Night.jpeg"
STANDARD_IMAGE="https://ik.imagekit.io/jgp5dmcfb/New_Iconic_Sheets_Set/1._Iconic_Sheet_Set_4pc_Light_Gray_Stack_2.jpg"


def get_product_type(sku):
    response=listings_client.get_listings_item(
        sellerId=SELLER_ID,
        sku=sku
    )
    return response.payload['summaries'][0]['productType']

def update_image(sku, product_type, image_path):

    patch_body = {
        "productType":product_type,
        "patches":[
            {
                "op":"replace",
                "path":"/attributes/main_product_image_locator", #other_product_image_locator_8
                "value":[
                    {
                        "media_location":image_path
                    }
                ]
            }
        ]
    }
    try:
        response = listings_client.patch_listings_item(
            sellerId=SELLER_ID,
            sku=sku,
            marketplaceIds=MARKETPLACE_IDS,
            body=patch_body
        )
        send_telegram_message(f"Image updated for {sku} with status {response.payload['status']}")
    except Exception as e:
        send_telegram_message(f"FAILED to update image for {sku}:\n{e}")


if __name__ == "__main__":
    args = sys.argv[1:]
    send_telegram_message(f"Starting cron job with argument {sys.argv[1:]}")
    
    for product in product_details:
        SKUS = product["skus"]
        image = product["STANDARD_IMAGE"]
        if len(args) > 1 and args[1] == "1":
            image = product["MORNING_IMAGE"]
        elif len(args) > 1 and args[1] == "2":
            image = product["EVENING_IMAGE"]
        product_type = get_product_type(SKUS[0])
        for sku in SKUS:
            update_image(sku, product_type=product_type, image_path=image)
            time.sleep(0.5)

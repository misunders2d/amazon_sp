from datetime import datetime, timedelta, timezone
from sp_api.base import ReportType, ApiResponse
from sp_api.api import Reports, CatalogItems

import os

from dotenv import load_dotenv

load_dotenv()


REFRESH_TOKEN_EU = os.environ["REFRESH_TOKEN_EU"]
REFRESH_TOKEN_US = os.environ["REFRESH_TOKEN_US"]

credentials = dict(
    refresh_token=REFRESH_TOKEN_US,
    lwa_app_id=os.environ["CLIENT_ID"],
    lwa_client_secret=os.environ["CLIENT_SECRET"],
)

report = Reports(credentials=credentials)


def get_asin_data(asin):
    catalog_items = CatalogItems(credentials=credentials)

    response = catalog_items.get_catalog_item(
        asin=asin,
        marketplaceIds=["ATVPDKIKX0DER"],
        includedData=[
            "images",
            "attributes",
            "summaries",
            "identifiers",
            # "classifications"#,"dimensions",,
            # "images","productTypes","salesRanks","relationships"#,"vendorDetails"
        ],
    )
    return response


def get_last_sunday(date: datetime | None = None):
    if not date:
        date = datetime.now()
    if not isinstance(date, datetime):
        raise BaseException("Date must be in datetime format")
    delta = date.isocalendar().weekday + 7
    last_sunday = date - timedelta(days=delta)
    return last_sunday


def all_orders_report(days=3) -> ApiResponse:
    response = report.create_report(
        reportType=ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL,
        dataStartTime=datetime.now() - timedelta(days=days),
    )

    report_id = response.payload["reportId"]
    print(f"report id: {report_id}")
    return response


def search_catalog_performance_report(week_start: datetime | None = None):
    if not week_start:
        week_start = get_last_sunday(datetime.now())
    report_options = {
        "reportPeriod": "WEEK",
    }
    response = report.create_report(
        reportType=ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
        reportOptions=report_options,
        dataStartTime=str(week_start.date()),
        dataEndTime=str(week_start.date() + timedelta(days=6)),
    )

    report_id = response.payload[
        "reportId"
    ]  # first search catalog performance report id: '3458825020258'
    print(f"report id: {report_id}")
    return response


def removal_order_report(days: int = 30):

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))

    response = report.create_report(
        reportType=ReportType.GET_FBA_FULFILLMENT_REMOVAL_ORDER_DETAIL_DATA,
        marketplaceIds=["ATVPDKIKX0DER"],
        dataStartTime=start,
        dataEndTime=end,
    )
    return response


def fba_inventory_data(days: int = 30):

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))

    response = report.create_report(
        reportType=ReportType.GET_EXCESS_INVENTORY_DATA,
        marketplaceIds=["ATVPDKIKX0DER"],
        dataStartTime=start,
        dataEndTime=end,
    )

    return response


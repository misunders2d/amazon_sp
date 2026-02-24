import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from dotenv import load_dotenv

# from sp_api.api import CatalogItems, Reports
from sp_api.asyncio.api import CatalogItems, Reports
from sp_api.base import ApiResponse, ReportType

load_dotenv()
REFRESH_TOKEN_EU = os.environ["REFRESH_TOKEN_EU"]
REFRESH_TOKEN_US = os.environ["REFRESH_TOKEN_US"]

credentials = dict(
    refresh_token=REFRESH_TOKEN_US,
    lwa_app_id=os.environ["CLIENT_ID"],
    lwa_client_secret=os.environ["CLIENT_SECRET"],
)


async def get_asin_data(asin):
    catalog_items = CatalogItems(credentials=credentials)

    response = await catalog_items.get_catalog_item(
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


def get_last_sunday(date: datetime | None = None, day_delta: int = 7):
    if not date:
        date = datetime.now()
    if not isinstance(date, datetime):
        raise BaseException("Date must be in datetime format")
    delta = date.isocalendar().weekday + day_delta
    last_sunday = date - timedelta(days=delta)
    return last_sunday


async def all_orders_report(days=3) -> ApiResponse:
    async with Reports(credentials=credentials) as report:
        response = await report.create_report(
            reportType=ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL,
            dataStartTime=datetime.now() - timedelta(days=days),
        )

    report_id = response.payload["reportId"]
    print(f"report id: {report_id}")
    return response


async def brand_analytics_report(
    week_start: datetime | None = None,
    report_type: Literal[
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
        ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT,
    ] = ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
    asin: str | None = None,
):
    """
    Creates a brand analytics report - search query performance or search catalog performance.
    """
    if not week_start:
        week_start = get_last_sunday(datetime.now())
    if not week_start.weekday() == 6:
        week_start = get_last_sunday(week_start, day_delta=0)
    report_options = {
        "reportPeriod": "WEEK",
    }
    if report_type == ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT:
        if not asin:
            raise BaseException("ASIN was not provided!")
        report_options["asin"] = asin
    async with Reports(credentials=credentials) as report:
        response = await report.create_report(
            reportType=report_type,
            reportOptions=report_options,
            dataStartTime=str(week_start.date()),
            dataEndTime=str(week_start.date() + timedelta(days=6)),
        )

    report_id = response.payload["reportId"]
    print(f"report id: {report_id}")
    return response


async def removal_order_report(days: int = 30):

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))

    async with Reports(credentials=credentials) as report:
        response = await report.create_report(
            reportType=ReportType.GET_FBA_FULFILLMENT_REMOVAL_ORDER_DETAIL_DATA,
            marketplaceIds=["ATVPDKIKX0DER"],
            dataStartTime=start,
            dataEndTime=end,
        )
    return response


async def fba_inventory_data(days: int = 30):

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))

    async with Reports(credentials=credentials) as report:
        response = await report.create_report(
            reportType=ReportType.GET_EXCESS_INVENTORY_DATA,
            marketplaceIds=["ATVPDKIKX0DER"],
            dataStartTime=start,
            dataEndTime=end,
        )

    return response

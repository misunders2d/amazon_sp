from datetime import datetime, timedelta, timezone
from typing import Literal

from sp_api.base import ApiResponse, ReportType

from base.authentication import get_reports_class
from base.rate_limits import rate_limit
from sp_utils.sp_utils import get_last_sunday


@rate_limit(max_rate=0.0167, burst_rate=15)
async def all_orders_report(
    days: int | None = 3,
    dataStartTime: datetime | None = None,
    dataEndTime: datetime | None = None,
) -> ApiResponse:
    if days and (dataStartTime or dataEndTime):
        raise ValueError(
            "Either `days` or `dataStartTime` / `dataEndTime` must be submitted, can't use both"
        )
    reportType = ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL
    dataStartTime = datetime.now() - timedelta(days=days) if days else dataStartTime

    async with get_reports_class() as report:
        return await report.create_report(
            reportType=reportType,
            dataStartTime=dataStartTime,
            dataEndTime=dataEndTime,
            marketplaceIds=["ATVPDKIKX0DER"],
        )


@rate_limit(max_rate=0.0167, burst_rate=15)
async def brand_analytics_report(
    week_start: datetime | str | None = None,
    report_type: Literal[
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
        ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT,
    ] = ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
    asin: str | None = None,
) -> ApiResponse:
    """
    Creates a brand analytics report - search query performance or search catalog performance.
    """
    if not week_start:
        week_start = get_last_sunday(datetime.now())
    if isinstance(week_start, str):
        week_start = datetime.strptime(week_start.split("T")[0], "%Y-%m-%d")
    if not week_start.weekday() == 6:
        week_start = get_last_sunday(week_start, day_delta=0)

    report_options = {"reportPeriod": "WEEK"}
    if report_type == ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT:
        if not asin:
            raise ValueError("ASIN was not provided!")
        report_options["asin"] = asin

    async with get_reports_class() as report:
        return await report.create_report(
            reportType=report_type,
            reportOptions=report_options,
            dataStartTime=str(week_start.date()),
            dataEndTime=str(week_start.date() + timedelta(days=6)),
            marketplaceIds=["ATVPDKIKX0DER"],
        )


@rate_limit(max_rate=0.0167, burst_rate=15)
async def removal_order_report(days: int = 30) -> ApiResponse:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))

    async with get_reports_class() as report:
        return await report.create_report(
            reportType=ReportType.GET_FBA_FULFILLMENT_REMOVAL_ORDER_DETAIL_DATA,
            dataStartTime=start,
            dataEndTime=end,
            marketplaceIds=["ATVPDKIKX0DER"],
        )


@rate_limit(max_rate=0.0167, burst_rate=15)
async def fba_inventory_data(days: int = 30) -> ApiResponse:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))

    async with get_reports_class() as report:
        return await report.create_report(
            reportType=ReportType.GET_EXCESS_INVENTORY_DATA,
            dataStartTime=start,
            dataEndTime=end,
            marketplaceIds=["ATVPDKIKX0DER"],
        )

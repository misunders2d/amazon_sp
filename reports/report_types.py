import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal

from sp_api.base import (
    ApiResponse,
    ReportType,
    SellingApiBadRequestException,
    SellingApiRequestThrottledException,
)

from base.authentication import get_reports_class
from sp_utils.sp_utils import get_last_sunday


async def create_report_with_retries(
    report_type: ReportType,
    data_start_time: str | datetime | None = None,
    data_end_time: str | datetime | None = None,
    report_options: dict | None = None,
    marketplace_ids: list = ["ATVPDKIKX0DER"],
    timeout: float = round(1 / 0.0167, 1) + 1,
    max_retries: int = 3,
) -> dict[str, str | ApiResponse | Exception]:
    """
    Main function to create any report with retries and max attempts.

    Args:
        report_type(ReporType): one of enumerated ReportType values (https://developer-docs.amazon.com/sp-api/docs/report-type-values)
        report_options(dict): a dict of report options specific to the relevant report_type
        dataStartTime(str): a start date in str representation
        dataEndTime(str): an end date in str representation
        timeout(float): number of seconds to wait between retries
        max_retries(int): number of retries after which the report is considered failed

    Returns:
        response(dict): a dict containing a failed/success status and a payload - either a response itself, or an error message
    """
    for attempt in range(1, max_retries + 1):
        try:
            async with get_reports_class() as report:
                response: ApiResponse = await report.create_report(
                    reportType=report_type,
                    reportOptions=report_options,
                    dataStartTime=data_start_time,
                    dataEndTime=data_end_time,
                    marketplaceIds=marketplace_ids,
                )
            report_id = response.payload["reportId"]
            print(f"report id: {report_id}")
            return {"status": "success", "payload": response}
        except SellingApiRequestThrottledException as e:
            print(f"Ran into rate limits, waiting for {timeout} seconds. {e}")
        except SellingApiBadRequestException as e:
            return {"status": "failed", "payload": f"SellingAPI error: {e}"}
        except Exception as e:
            return {"status": "failed", "payload": e}

        if attempt < max_retries:
            await asyncio.sleep(timeout)
    return {
        "status": "failed",
        "payload": f"Reached max {max_retries} attempts, no success",
    }


async def all_orders_report(days=3) -> ApiResponse:
    reportType = ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL
    dataStartTime = datetime.now() - timedelta(days=days)

    response_obj = await create_report_with_retries(
        report_type=reportType, data_start_time=dataStartTime
    )
    if response_obj["status"] == "success" and isinstance(
        response_obj["payload"], ApiResponse
    ):
        response = response_obj["payload"]
        return response
    else:
        return ApiResponse(errors=response_obj["payload"])


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
    report_options = {
        "reportPeriod": "WEEK",
    }
    if report_type == ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT:
        if not asin:
            raise BaseException("ASIN was not provided!")
        report_options["asin"] = asin
    response_obj = await create_report_with_retries(
        report_type=report_type,
        report_options=report_options,
        data_start_time=str(week_start.date()),
        data_end_time=str(week_start.date() + timedelta(days=6)),
    )
    if response_obj["status"] == "success" and isinstance(
        response_obj["payload"], ApiResponse
    ):
        response = response_obj["payload"]
        return response
    else:
        return ApiResponse(errors=response_obj["payload"])


async def removal_order_report(days: int = 30):
    reportType = ReportType.GET_FBA_FULFILLMENT_REMOVAL_ORDER_DETAIL_DATA
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))
    marketplaceIds = ["ATVPDKIKX0DER"]

    response_obj = await create_report_with_retries(
        report_type=reportType,
        data_start_time=start,
        data_end_time=end,
        marketplace_ids=marketplaceIds,
    )

    if response_obj["status"] == "success" and isinstance(
        response_obj["payload"], ApiResponse
    ):
        response = response_obj["payload"]
        report_id = response.payload["reportId"]
        print(f"report id: {report_id}")
        return response
    else:
        return ApiResponse(errors=response_obj["payload"])


async def fba_inventory_data(days: int = 30):
    reportType = ReportType.GET_EXCESS_INVENTORY_DATA
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(days, 90))
    marketplaceIds = ["ATVPDKIKX0DER"]

    response_obj = await create_report_with_retries(
        report_type=reportType,
        data_start_time=start,
        data_end_time=end,
        marketplace_ids=marketplaceIds,
    )

    if response_obj["status"] == "success" and isinstance(
        response_obj["payload"], ApiResponse
    ):
        response = response_obj["payload"]
        report_id = response.payload["reportId"]
        print(f"report id: {report_id}")
        return response
    else:
        return ApiResponse(errors=response_obj["payload"])

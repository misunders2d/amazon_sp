import asyncio
import json
import logging
from json import JSONDecodeError
from typing import List, Literal

from sp_api.base import ApiResponse, ReportType

from base.authentication import get_reports_class
from base.rate_limits import SP_API_RATE_LIMITS, rate_limit

logging.basicConfig(
    filename="sqp_log.log",
    filemode="a",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@rate_limit(**SP_API_RATE_LIMITS["get_report"])
async def _poll_until_done(report_id: str, sleep_time=5) -> dict:
    """
    Check report status until the report is fully resolved - either Done, or failed
    Args:
        report_id(str): the id of the report to check
        sleep_time(int): Optional. The time in seconds to wait between polls

    Returns:
        report_status(dict): The dict containing the status of the report,
        document id, report creation time etc
    """
    async with get_reports_class() as report:
        status_job = await report.get_report(reportId=report_id)
        report_status = status_job.payload

        while report_status.get("processingStatus") in ("IN_PROGRESS", "IN_QUEUE"):
            print(f"Waiting for {sleep_time} seconds")
            await asyncio.sleep(sleep_time)
            status_job = await report.get_report(reportId=report_id)
            report_status = status_job.payload
            print(f"report status: {report_status['processingStatus']}")

    return report_status


@rate_limit(**SP_API_RATE_LIMITS["get_report_document"])
async def _download_document(report_document_id: str) -> str | dict:
    """
    Downloads the document from the generated Amazon report.
    Args:
        report_document_id(str): an id of the document (i.e. "amzn1.spdoc.1.4.na.ec5333cc-a174-4510-9bfb-3aebf0fec4fe.T18BMIED8ZJ38Q.230 00")

    Returns:
        document(dict | str): the contents of the document in json or str format if successful or an empty string if failed.
    """
    async with get_reports_class() as report:
        report_document_obj = await report.get_report_document(
            reportDocumentId=report_document_id,
            download=True,
        )
    try:
        return json.loads(report_document_obj.payload["document"])
    except JSONDecodeError:
        return report_document_obj.payload["document"]
    except Exception as e:
        print(f"Failed to download document {report_document_id}. Error: {e}")
    return ""


async def check_and_download_report(
    response: ApiResponse | None = None, report_id: str | None = None
) -> str | dict:
    """
    Checks and downloads the report from a generated report response.

    Args:
        response(ApiResponse): Optional. Response from the `create_report` function.
        report_id(str): Optional. Actual report id.
        Must provide either response or report_id (or both)
        timeout(int): Optional. Timeout in seconds
    """
    report_id = response.payload["reportId"] if response is not None else report_id
    if all([response is None, report_id is None]) or not report_id:
        raise ValueError("Either a response or a report ID must be provided")

    report_status = await _poll_until_done(report_id)

    if report_status["processingStatus"] != "DONE":
        print(f"report status: {report_status['processingStatus']}")
        return ""

    print(f"document id: {report_status['reportDocumentId']}")
    return await _download_document(report_status["reportDocumentId"])


@rate_limit(**SP_API_RATE_LIMITS["get_reports"])
async def _fetch_first_page(
    report_types: list[ReportType] = [
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT
    ],
    processing_statuses: List[
        Literal["CANCELLED", "DONE", "FATAL", "IN_PROGRESS", "IN_QUEUE"]
    ] = ["DONE"],
    created_since=None,
    created_before=None,
) -> ApiResponse:
    async with get_reports_class() as report:
        return await report.get_reports(
            reportTypes=report_types,
            processingStatuses=processing_statuses,
            createdSince=created_since,
            createdUntil=created_before,
            pageSize=100,
        )


@rate_limit(**SP_API_RATE_LIMITS["get_reports"])
async def fetch_reports(
    report_types: list[ReportType] = [
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT
    ],
    processing_statuses: List[
        Literal["CANCELLED", "DONE", "FATAL", "IN_PROGRESS", "IN_QUEUE"]
    ] = ["DONE"],
    created_since=None,
    created_before=None,
):
    """
    Queries Amazon for already created report for the time period.
    """
    all_reports = []
    first_page = await _fetch_first_page(
        report_types=report_types,
        processing_statuses=processing_statuses,
        created_since=created_since,
        created_before=created_before,
    )
    if not first_page.errors:
        all_reports.extend(first_page.payload["reports"])
        next_token = first_page.next_token
        page = 2
        while next_token:
            print(
                f"Pulling next page ({page}). Currently {len(all_reports)} reports colected"
            )
            async with get_reports_class() as report:
                r = await report.get_reports(nextToken=next_token)
                all_reports.extend(r.payload["reports"])
                next_token = r.next_token
                page += 1
    return all_reports

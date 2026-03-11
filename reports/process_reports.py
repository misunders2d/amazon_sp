import asyncio
import json
import logging
from json import JSONDecodeError
from typing import List, Literal

from sp_api.base import (
    ApiResponse,
    ReportType,
    SellingApiBadRequestException,
    SellingApiRequestThrottledException,
)

from base.authentication import get_reports_class

logging.basicConfig(
    filename="sqp_log.log",
    filemode="a",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


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


async def _download_document(
    report_document_id: str, timeout=2, max_retries=3
) -> str | dict:
    """
    Downloads the document from the generated Amazon report.
    Args:
        report_document_id(str): an id of the document (i.e. "amzn1.spdoc.1.4.na.ec5333cc-a174-4510-9bfb-3aebf0fec4fe.T18BMIED8ZJ38Q.230 00")
        timeout(int): number of seconds between attempts.
        max_retries(int): number of attempts to redownload if hitting rate limits.

    Returns:
        document(dict | str): the contents of the document in json or str format if successful or an empty string if failed.
    """
    backoff = int(1 / 0.0167) + 2
    for attempt in range(1, max_retries + 1):
        try:
            async with get_reports_class() as report:
                report_document_obj = await report.get_report_document(
                    reportDocumentId=report_document_id,
                    download=True,
                    timeout=timeout,
                )
            try:
                return json.loads(report_document_obj.payload["document"])
            except JSONDecodeError:
                return report_document_obj.payload["document"]
        except SellingApiRequestThrottledException:
            print(
                f"Hit rate limits (attempt {attempt}/{max_retries}), sleeping for {backoff}s"
            )
        except Exception as e:
            print(f"Unknown error on attempt {attempt}/{max_retries}: {e}")
        if attempt < max_retries:
            await asyncio.sleep(backoff)

    print(
        f"Failed to download document {report_document_id} after {max_retries} attempts"
    )
    return ""


async def check_and_download_report(
    response: ApiResponse | None = None, report_id: str | None = None, timeout=5
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
    return await _download_document(report_status["reportDocumentId"], timeout=timeout)


async def _fetch_first_page(
    report_types: list[ReportType] = [
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT
    ],
    processing_statuses: List[
        Literal["CANCELLED", "DONE", "FATAL", "IN_PROGRESS", "IN_QUEUE"]
    ] = ["DONE"],
    created_since=None,
    created_before=None,
    sleep_time=round(1 / 0.0222, 0) + 1,
    max_retries=3,
) -> ApiResponse:
    for attempt in range(1, max_retries + 1):
        async with get_reports_class() as report:
            try:
                r = await report.get_reports(
                    reportTypes=report_types,
                    processingStatuses=processing_statuses,
                    createdSince=created_since,
                    createdUntil=created_before,
                    pageSize=100,
                )
                return r
            except SellingApiRequestThrottledException as e:
                print(
                    f"Ran into rate limits on {attempt} attempt, retrying after {sleep_time} seconds:\n{e}"
                )
            except Exception as e:
                return ApiResponse(errors=e)
            if attempt < max_retries:
                await asyncio.sleep(sleep_time)
    return ApiResponse(
        errors=f"Could not retrieve list of reports with {max_retries} attempts"
    )


async def fetch_reports(
    report_types: list[ReportType] = [
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT
    ],
    processing_statuses: List[
        Literal["CANCELLED", "DONE", "FATAL", "IN_PROGRESS", "IN_QUEUE"]
    ] = ["DONE"],
    created_since=None,
    created_before=None,
    sleep_time=round(1 / 0.0222, 0) + 1,
    max_retries=3,
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
            try:
                async with get_reports_class() as report:
                    r = await report.get_reports(nextToken=next_token)
                    all_reports.extend(r.payload["reports"])
                    next_token = r.next_token
                    page += 1
            except SellingApiRequestThrottledException:
                print(f"Ran out of rate limits, waiting for {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
            except SellingApiBadRequestException as e:
                print(f"Ran into an api exception: {e}")
            except Exception as e:
                print(f"Unknown error: {e}")
    return all_reports

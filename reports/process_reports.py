import json
import logging
import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import List, Literal

import pandas as pd
import pandas_gbq
from sp_api.base import (
    ApiResponse,
    ReportType,
    SellingApiBadRequestException,
    SellingApiRequestThrottledException,
)

from connection import bigquery, connect_to_bigquery, create_credentials
from telegram_notifier import send_telegram_message

from . import all_orders_report, report

logging.basicConfig(
    filename="sqp_log.log",
    filemode="a",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def check_and_download_report(
    response: ApiResponse | None = None, report_id: str | None = None, timeout=5
):
    rate_limit = 0.0167
    if all([response is None, report_id is None]):
        raise ValueError("Either a response or a report ID must be provided")

    report_id = response.payload["reportId"] if response is not None else report_id
    report_status = report.get_report(reportId=report_id).payload

    while report_status["processingStatus"] in ("IN_PROGRESS", "IN_QUEUE"):
        print("Waiting for 10 seconds")
        time.sleep(10)
        report_status = report.get_report(reportId=report_id).payload
        print(f"report status: {report_status['processingStatus']}")

    if report_status["processingStatus"] == "DONE":
        try:
            report_document_obj = report.get_report_document(
                reportDocumentId=report_status["reportDocumentId"],
                download=True,
                timeout=timeout,
            )
            try:
                report_document = json.loads(report_document_obj.payload["document"])
            except JSONDecodeError:
                report_document = report_document_obj.payload["document"]
        except SellingApiRequestThrottledException:
            print(f"Hit rate limits, sleeping for {int(1/rate_limit)+2} seconds")
            time.sleep(int(1 / rate_limit) + 2)
            report_document = check_and_download_report(
                report_id=report_id, timeout=int(1 / rate_limit) + 2
            )

        except Exception as e:
            print(f"Unknown error occurred, cooling down and retrying.\n Error: {e}")
            time.sleep(int(1 / rate_limit) + 2)
            report_document = check_and_download_report(
                report_id=report_id, timeout=int(1 / rate_limit) + 2
            )

        print(f"document id: {report_status['reportDocumentId']}")
    else:
        print(f"report status: {report_status['processingStatus']}")
        report_document = ""
    return report_document


def fetch_reports(
    report_types: list = [
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT
    ],
    processing_statuses: List[
        Literal["CANCELLED", "DONE", "FATAL", "IN_PROGRESS", "IN_QUEUE"]
    ] = [],
    created_since=None,
    created_before=None,
):
    """
    Queries Amazon for already created report for the time period.
    """
    sleep_time = round(1 / 0.0222, 2) + 1
    all_reports = []
    r = report.get_reports(
        reportTypes=report_types,
        processingStatuses=processing_statuses,
        createdSince=created_since,
        createdUntil=created_before,
        pageSize=100,
    )
    all_reports.extend(r.payload["reports"])
    next_token = r.next_token
    page = 2
    while next_token:
        print(
            f"Pulling next page ({page}), sleeping for {sleep_time} seconds. Currently {len(all_reports)} reports colected"
        )
        time.sleep(sleep_time)
        try:
            r = report.get_reports(nextToken=next_token)
            all_reports.extend(r.payload["reports"])
            next_token = r.next_token
            page += 1
        except (SellingApiBadRequestException, SellingApiRequestThrottledException):
            print(f"Ran out of limits, waiting for {sleep_time} seconds")
            time.sleep(sleep_time)
        except Exception as e:
            print(f"Unknown error: {e}")
    return all_reports


def check_if_ba_report_exists(document):
    asins = document["reportSpecification"].get("reportOptions", {}).get("asin")
    print("Checking asins: ")
    print(asins)
    asins = [x.strip() for x in asins.split()]
    start_date = datetime.strptime(
        document["reportSpecification"].get("dataStartTime"), "%Y-%m-%d"
    ).date()
    period = (
        document["reportSpecification"].get("reportOptions", {}).get("reportPeriod")
    )

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("asins", "STRING", asins),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("period", "STRING", period),
        ]
    )
    query = """
    SELECT DISTINCT asin
    FROM `mellanni-project-da.auxillary_development.sqp_asin_weekly`
    WHERE DATE(startDate) = @start_date
      AND period = @period
      AND asin IN UNNEST(@asins)
      """

    with connect_to_bigquery() as client:
        bq_result = client.query(query, job_config=job_config)
    duplicate_asins = {x.asin for x in bq_result}
    unique_asins = [x for x in asins if x not in duplicate_asins]
    if duplicate_asins:
        print(
            f"[[DUPLICATES]] {len(duplicate_asins)} duplicate asins found for {start_date} {period}: ",
            ", ".join(duplicate_asins),
        )
    if unique_asins:
        print(
            f"[[UNIQUE]] {len(unique_asins)} unique asins found for {start_date} {period}: ",
            ", ".join(unique_asins),
        )
    return unique_asins


def process_document(document):
    result = pd.DataFrame()
    columns = dict()

    def process_row(row, prefix=None):
        for key, value in row.items():
            if isinstance(value, dict):
                process_row(value, prefix=key)
            else:
                key = f"{prefix}_{key}" if prefix else key
                columns[key] = value
        return columns

    for row in document["dataByAsin"]:
        columns = process_row(row)
        result = pd.concat(
            [
                result,
                pd.DataFrame(data=[columns.values()], columns=pd.Index(columns.keys())),
            ]
        )
    period = (
        document["reportSpecification"].get("reportOptions", {}).get("reportPeriod")
    )
    asins = document["reportSpecification"].get("reportOptions", {}).get("asin")
    asins = [x.strip() for x in asins.split()]

    start_date = datetime.strptime(
        document["reportSpecification"].get("dataStartTime"), "%Y-%m-%d"
    ).date()
    marketplaces = document["reportSpecification"].get("marketplaceIds", [])

    if len(document["dataByAsin"]) == 0:

        result["asin"] = asins
        result["startDate"] = start_date

    result["period"] = period
    result["marketplaces"] = ", ".join(sorted(marketplaces))
    return result


def upload_ba_report(document):
    executor = ThreadPoolExecutor()

    unique_asins_job = executor.submit(check_if_ba_report_exists, document)
    report_df_job = executor.submit(process_document, document)

    unique_asins = unique_asins_job.result()
    report_df = report_df_job.result()

    report_to_upload = report_df.loc[report_df["asin"].isin(unique_asins)]
    if len(report_to_upload) == 0:
        print("[[RESULT]] All records are duplicates, skipping")
    else:
        print(f"[[RESULT]] Uploading {len(report_to_upload)} rows to bigquery")
        pandas_gbq.to_gbq(
            report_to_upload,
            destination_table="mellanni-project-da.auxillary_development.sqp_asin_weekly",
            credentials=create_credentials(),
            if_exists="append",
        )


def pull_multiple_documents(all_reports: list | None = None):
    pkl_file = "/home/misunderstood/Downloads/documents.pkl"
    if not all_reports:
        all_reports = fetch_reports(processing_statuses=[])
    print(len(all_reports))

    all_reports = [x for x in all_reports if x["processingStatus"] != "FATAL"]

    def pickle_dump(obj):
        with open(pkl_file, "wb") as f:
            pickle.dump(obj, f)

    if not os.path.isfile(pkl_file):
        all_documents = {}
    else:
        with open(pkl_file, "rb") as f:
            all_documents = pickle.load(f)

    for report_obj in all_reports[::-1]:
        if report_obj["reportId"] not in all_documents:
            document = check_and_download_report(report_id=report_obj["reportId"])
            all_documents[report_obj["reportId"]] = document
            pickle_dump(all_documents)
            print(f"{len(all_documents)} retrieved")
            # time.sleep(1 / 0.0167)
            upload_ba_report(document)
            print("Cancel the job now if you want to stop")
            time.sleep(2)

        else:
            print("Document already retrieved")


def collect_sqp_reports(created_since, created_before):
    print(f"[[DATE: {created_since} to {created_before}]]")
    created_since = (
        created_since.isoformat()
        if isinstance(created_since, datetime)
        else created_since
    )
    created_before = (
        created_before.isoformat()
        if isinstance(created_before, datetime)
        else created_before
    )

    try:
        all_reports = fetch_reports(
            report_types=[
                ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT
            ],
            processing_statuses=["DONE"],
            created_since=created_since,
            created_before=created_before,
        )
        for i, report_record in enumerate(all_reports, start=1):
            document = check_and_download_report(report_id=report_record["reportId"])
            _ = upload_ba_report(document=document)
            print(f"Uploaded {i} reports of {len(all_reports)}", end="\n\n")
    except Exception as e:
        print(f"[[ERROR for {str(e)}]]: {e}\nRetrying...")
        collect_sqp_reports(
            created_since=created_since,
            created_before=created_before,
        )


if __name__ == "__main__":
    # report_ids_df = pd.read_excel(
    #     "/home/misunderstood/Downloads/sqp asin report ids.xlsx"
    # )
    # report_ids = report_ids_df["reportId"].values.tolist()
    # all_reports = [{"reportId": x, "processingStatus": "DONE"} for x in report_ids]
    # pull_multiple_documents(all_reports)
    created_before = datetime.now()
    threshold = created_before - timedelta(days=3)
    created_since = created_before - timedelta(days=1)
    send_telegram_message(
        message=f"Starting SQP reports update for {created_since.date()} - {created_before.date()}"
    )
    while created_since > threshold:
        collect_sqp_reports(
            created_since=created_since,
            created_before=created_before,
        )
        logging.debug(
            msg=f"[[REPORT]]: pushed data for {created_since} day\n[[END OF REPORT]]\n"
        )
        print(f"[[REPORT]]: pushed data for {created_since} day\n[[END OF REPORT]]\n")
        created_before, created_since = created_since, created_since - timedelta(days=1)

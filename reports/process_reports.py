import time, json
from json import JSONDecodeError
from datetime import timedelta, date, datetime
from sp_api.base import ReportType, SellingApiBadRequestException, SellingApiRequestThrottledException, ApiResponse

from . import search_catalog_performance_report, all_orders_report, report

from connection import connect_to_bigquery

def check_and_download_report(response: ApiResponse | None = None, report_id: str | None = None):
    if all([response is None, report_id is None]):
        raise ValueError("Either a response or a report ID must be provided")
    
    report_id = response.payload['reportId'] if response is not None else report_id
    report_status = report.get_report(reportId=report_id).payload

    while report_status['processingStatus'] in ('IN_PROGRESS','IN_QUEUE'):
        print('Waiting for 10 seconds')
        time.sleep(10)
        report_status = report.get_report(reportId=report_id).payload
        print(f"report status: {report_status['processingStatus']}")

    if report_status['processingStatus']=='DONE':
        report_document_obj = report.get_report_document(
            reportDocumentId = report_status['reportDocumentId'],
            download=True)
        try:
            report_document = json.loads(report_document_obj.payload['document'])
        except JSONDecodeError:
            report_document = report_document_obj.payload['document']
        print(f"document id: {report_status['reportDocumentId']}")
    else:
        print(f"report status: {report_status['processingStatus']}")
        report_document = ''
    return report_document


def fetch_reports(
        report_types:list=[ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT],
        processing_statuses:list=[str],
        created_since=datetime.now() - timedelta(days=90)
        ):
    sleep_time = round(1/0.0222,2)
    all_reports = []
    r = report.get_reports(
        reportTypes=report_types,
        processingStatuses=processing_statuses,
        createdSince=created_since,
        pageSize=100)
    all_reports.extend(r.payload['reports'])
    next_token = r.next_token
    while next_token:
        print(f'Pulling next page, sleeping for {sleep_time} seconds')
        time.sleep(sleep_time)
        try:
            r = report.get_reports(nextToken=next_token)
            all_reports.extend(r.payload['reports'])
            next_token = r.next_token
        except (SellingApiBadRequestException, SellingApiRequestThrottledException):
            print(f'Ran out of limits, waiting for {sleep_time} seconds')
            time.sleep(20)
        except Exception as e:
            print(f"Unknown error: {e}")
    return all_reports


def request_scp_data():
    week_start = date(2024, 2, 18)
    
    while week_start <= date(2025,6,13):
        try:
            search_catalog_performance_report(week_start)
            time.sleep(20)
            week_start = week_start + timedelta(days=7)
        except (SellingApiBadRequestException, SellingApiRequestThrottledException):
            print('Ran out of limits, waiting for 60 seconds')
            time.sleep(60)


def pull_multiple_documents():
    all_reports = fetch_reports(processing_statuses=[])
    print(len(all_reports))

    all_reports = [x for x in all_reports if x['processingStatus'] != "FATAL"]

    import pickle
    def pickle_dump(obj):
        with open('/home/misunderstood/Downloads/documents.pkl','wb') as f:
            pickle.dump(obj, f)

    all_documents = {}
    for report_obj in all_reports[::-1]:
        if report_obj['reportId'] not in all_documents:
            try:
                document = check_and_download_report(report_id=report_obj['reportId'])
                all_documents[report_obj['reportId']] = document
                pickle_dump(all_documents)
                print(f'{len(all_documents)} retrieved')
                time.sleep(1/0.0167)
            except (SellingApiBadRequestException, SellingApiRequestThrottledException):
                print(f'Ran out of limits, waiting for {1/0.0167} seconds')
                time.sleep(1/0.0167)
        else:
            print('Document already retrieved')


if __name__ == "__main__":
    today = datetime.now().date()
    response = all_orders_report()
    report_document = check_and_download_report(response)
    with open(f'/home/misunderstood/temp/All Orders {str(today)}.txt','w') as f:
        f.write(report_document)
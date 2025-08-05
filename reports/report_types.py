from datetime import datetime, timedelta
from sp_api.base import ReportType, ApiResponse
from sp_api.api import  Reports

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()


REFRESH_TOKEN_EU=os.environ['REFRESH_TOKEN_EU']
REFRESH_TOKEN_US=os.environ['REFRESH_TOKEN_US']

credentials = dict(
    refresh_token=REFRESH_TOKEN_US,
    lwa_app_id=os.environ['CLIENT_ID'],
    lwa_client_secret=os.environ['CLIENT_SECRET']
)

report = Reports(credentials=credentials)

def get_last_sunday(date:datetime = None):
    if not date:
        date = datetime.now().date()
    if not isinstance(date, datetime):
        raise BaseException("Date must be in datetime format")
    delta = date.isocalendar().weekday + 7
    last_sunday = date - timedelta(days=delta)
    return last_sunday.date()

def all_orders_report(days=3) -> ApiResponse:
    response = report.create_report(
        reportType=ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL,
        dataStartTime = datetime.now() - timedelta(days=days)
        )

    report_id = response.payload['reportId']
    print(f'report id: {report_id}')
    return response


def search_catalog_performance_report(week_start: datetime = None):
    if not week_start:
        week_start = get_last_sunday(datetime.now())
    report_options = {
        "reportPeriod":'WEEK',
    }
    response = report.create_report(
        reportType=ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
        reportOptions=report_options,
        dataStartTime=str(week_start),
        dataEndTime=str(week_start + timedelta(days=6))
        )

    report_id = response.payload['reportId'] # first search catalog performance report id: '3458825020258'
    print(f'report id: {report_id}')
    return response
from datetime import datetime, timedelta
from sp_api.base import ReportType, ApiResponse

from .report_init import report

def all_orders_report() -> ApiResponse:
    response = report.create_report(
        reportType=ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL,
        dataStartTime = datetime.now() - timedelta(days=3)
        )

    report_id = response.payload['reportId']
    print(f'report id: {report_id}')
    return response



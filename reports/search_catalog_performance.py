
from datetime import timedelta
from sp_api.base import ReportType

from .report_init import report

def search_catalog_performance_report(week_start):
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



import time
from datetime import datetime, timedelta
from sp_api.base import ReportType
from sp_api.api import  Reports

import os


REFRESH_TOKEN_EU=os.environ['REFRESH_TOKEN_EU']
REFRESH_TOKEN_US=os.environ['REFRESH_TOKEN_US']

#create credentials dictionary
credentials = dict(
    refresh_token=REFRESH_TOKEN_US,
    lwa_app_id=os.environ['CLIENT_ID'],
    lwa_client_secret=os.environ['CLIENT_SECRET']
)

#instantiate a "report" object from "Reports" class with our credentials
report = Reports(credentials=credentials)

#create a request report
response = report.create_report(
    reportType=ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL,
    dataStartTime = datetime.now() - timedelta(days=3)
    )

#get a report id
report_id = response.payload['reportId']
print(f'report id: {report_id}')

#get report status (IN_PROGRESS, CANCELLED etc)
report_status = report.get_report(reportId=report_id).payload

#If report is still generating (status == IN_PROGRESS), wait 30 seconds and update the status
while report_status['processingStatus'] in ('IN_PROGRESS','IN_QUEUE'):
    print('Waiting for 30 seconds')
    time.sleep(30)
    report_status = report.get_report(reportId=report_id).payload
    print(f'report status: {report_status['processingStatus']}')
    #if the report status is no longer "IN_PROGRESS", we can download the "report document"

if report_status['processingStatus']=='DONE':
    report_document = report.get_report_document(
        reportDocumentId = report_status['reportDocumentId'],
        download=True,
        file='All Orders.txt')
    print(f'document id: {report_status['reportDocumentId']}')
else:
    print(f'report status: {report_status['processingStatus']}')


    
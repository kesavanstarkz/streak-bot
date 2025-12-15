from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Path to your credentials file
SERVICE_ACCOUNT_FILE = 'credientials/cred.json'
SPREADSHEET_ID = '1oQq7m0qMQadxeDZBGER4WXUvI7iwk2yM-yzKCi82pS4'  # Your sheet ID
RANGE_NAME = 'Sheet1!A1'

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
service = build('sheets', 'v4', credentials=creds)

values = [['Test', 'Write', 'Success']]
body = {'values': values}

result = service.spreadsheets().values().append(
    spreadsheetId=SPREADSHEET_ID,
    range=RANGE_NAME,
    valueInputOption='RAW',
    insertDataOption='INSERT_ROWS',
    body=body
).execute()

print(f"{result.get('updates').get('updatedRows')} rows updated.")
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_test_sheet(credentials_path, share_email):
    logging.info("Starting the creation of the test sheet...")
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    try:
        credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
        logging.info("Authentication successful.")
    except Exception as e:
        logging.error(f"Authentication failed: {str(e)}")
        return

    try:
        service = build('sheets', 'v4', credentials=credentials)
        drive_service = build('drive', 'v3', credentials=credentials)
    except Exception as e:
        logging.error(f"Failed to create API services: {str(e)}")
        return

    # Create spreadsheet
    spreadsheet = {'properties': {'title': 'TEST SHEET'}}
    try:
        spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']
        logging.info(f"Spreadsheet created: {spreadsheet_id}")
        logging.info(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    except Exception as e:
        logging.error(f"Failed to create spreadsheet: {str(e)}")
        return

    # Share the spreadsheet
    try:
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={
                'type': 'user',
                'role': 'writer',
                'emailAddress': share_email
            }
        ).execute()
        logging.info(f"Spreadsheet shared with {share_email}")
    except Exception as e:
        logging.error(f"Failed to share spreadsheet: {str(e)}")

    # Insert data
    values = [['Column 1'], ['success']]
    body = {'values': values}
    try:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        logging.info("Data uploaded successfully.")
    except Exception as e:
        logging.error(f"Failed to upload data: {str(e)}")

if __name__ == "__main__":
    credentials_path = '../service_account.json'  # Path to your service account JSON
    share_email = 'growyourbiz4ever@gmail.com'  # Email to share the sheet with
    create_test_sheet(credentials_path, share_email)

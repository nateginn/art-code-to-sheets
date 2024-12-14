import os
import logging
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_test_sheet_with_data(credentials_path, share_email, json_data_path):
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
    spreadsheet = {'properties': {'title': 'TEST SHEET WITH DATA'}}
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
        return

    # Load JSON data
    try:
        with open(json_data_path, 'r') as f:
            data = json.load(f)
        logging.info("JSON data loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load JSON data: {str(e)}")
        return

    # Prepare data for Google Sheets
    headers = ["Name", "DOB", "Provider"]
    values = [headers]
    for patient in data.get('patients', []):
        values.append([patient['name'], patient['birthday'], patient['provider']])

    # Update the sheet with headers and data
    try:
        body = {'values': values}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        logging.info("Data uploaded to Google Sheet successfully.")
    except Exception as e:
        logging.error(f"Failed to upload data to Google Sheet: {str(e)}")


if __name__ == "__main__":
    credentials_path = '../../service_account.json'  # Path to your service account JSON
    share_email = 'growyourbiz4ever@gmail.com'  # Email to share the sheet with
    json_data_path = '../../artschedretriever/agenda_data.json'  # Path to the JSON data file
    create_test_sheet_with_data(credentials_path, share_email, json_data_path)

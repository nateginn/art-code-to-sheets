import json
import os
from sheets_integration import SheetsManager


def test_upload_json_to_sheets():
    # Path to the JSON data file
    json_data_path = '../../artschedretriever/agenda_data.json'
    credentials_path = '../../service_account.json'  # Path to your service account JSON
    share_email = 'growyourbiz4ever@gmail.com'  # Email to share the sheet with

    # Load JSON data
    try:
        with open(json_data_path, 'r') as f:
            data = json.load(f)
        print("JSON data loaded successfully.")
    except Exception as e:
        print(f"Failed to load JSON data: {str(e)}")
        return

    # Initialize SheetsManager
    sheets_manager = SheetsManager(credentials_path)

    # Prepare data for Google Sheets
    location = "UNC"  # Example location, adjust as needed
    service_date = data['date_of_service']
    patients_data = data['patients']

    # Create and format the sheet
    folder_id = '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw'  # Google Drive folder ID
    spreadsheet_id = sheets_manager.create_and_format_sheet(location, service_date, patients_data, folder_id)

    if spreadsheet_id:
        print("Successfully exported to Google Sheets")
    else:
        print("Failed to export to Google Sheets")


if __name__ == "__main__":
    test_upload_json_to_sheets()

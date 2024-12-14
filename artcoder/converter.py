import tabula
import pandas as pd
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
from datetime import datetime

def extract_and_upload_to_sheets(pdf_path, sheet_name, credentials_path):
    """
    Extract data from PDF and upload to Google Sheets
    
    Args:
        pdf_path (str): Path to the PDF file
        sheet_name (str): Name for the new Google Sheet
        credentials_path (str): Path to Google Sheets API credentials JSON file
    """
    try:
        # Extract tables from PDF
        print("Extracting tables from PDF...")
        tables = tabula.read_pdf(pdf_path, pages='all')
        
        # Get the header date - modified this part
        header_text = None
        for column in tables[0].columns:
            if isinstance(column, str) and "Schedule Standard view" in column:
                header_text = column
                break
                
        if header_text:
            date_obj = datetime.strptime(header_text.split(' - ')[1], '%A, %B %d, %Y')
            formatted_date = date_obj.strftime('%m/%d/%y')
        else:
            formatted_date = datetime.now().strftime('%m/%d/%y')
            
        # Combine all tables into one DataFrame if multiple tables exist
        if len(tables) > 1:
            df = pd.concat(tables, ignore_index=True)
        else:
            df = tables[0]
            
        # Remove rows with birth dates and phone numbers
        df = df[~df['PATIENT'].str.contains(r'^\d{2}/\d{2}/\d{4}|M\.', na=False)]
        
        # Add date column at the beginning
        df.insert(0, 'DATE', formatted_date)
        
        # Clean the data
        df = df.fillna('')  # Replace NaN values with empty strings
        
        # Authenticate with Google Sheets API
        print("Authenticating with Google Sheets...")
        scopes = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive']
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=scopes)
        
        # Create Google Sheets service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Create new spreadsheet
        print("Creating new spreadsheet...")
        spreadsheet = {
            'properties': {
                'title': sheet_name
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']
        
        # Share the spreadsheet with your email
        drive_service = build('drive', 'v3', credentials=credentials)
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={
                'type': 'user',
                'role': 'writer',
                'emailAddress': 'growyourbiz4ever@gmail.com'
            }
        ).execute()
        
        # Convert DataFrame to list of lists for Google Sheets
        values = [df.columns.tolist()] + df.values.tolist()
        
        # Prepare the data for upload
        body = {
            'values': values
        }
        
        # Upload data to the spreadsheet
        print("Uploading data...")
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"Successfully created spreadsheet with ID: {spreadsheet_id}")
        return spreadsheet_id
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def upload_json_to_sheets(json_data, sheets_manager):
    """
    Upload JSON data to Google Sheets.
    Args:
        json_data (dict): The JSON data to upload.
        sheets_manager (SheetsManager): An instance of SheetsManager for Google Sheets operations.
    """
    try:
        # Extract data from JSON
        date_of_service = json_data.get("date_of_service", "")
        patients = json_data.get("patients", [])

        # Prepare data for Google Sheets
        values = [["Date of Service", "Name", "Birthday", "Provider"]]  # Headers
        for patient in patients:
            values.append([
                date_of_service,
                patient.get("name", ""),
                patient.get("birthday", ""),
                patient.get("provider", "")
            ])

        # Upload to Google Sheets
        spreadsheet_id = sheets_manager.create_sheet("Agenda Data")
        sheets_manager.update_values(spreadsheet_id, "Sheet1", values)
        print("Data uploaded successfully to Google Sheets.")
    except Exception as e:
        print(f"Error uploading data to Google Sheets: {e}")

def main():
    # Example usage
    pdf_path = './Practice Fusion.pdf'
    sheet_name = 'Converted PDF Data'
    credentials_path = './credentials.json'
    
    result = extract_and_upload_to_sheets(pdf_path, sheet_name, credentials_path)
    
    if result:
        print("Conversion completed successfully!")
    else:
        print("Conversion failed.")

if __name__ == "__main__":
    main()

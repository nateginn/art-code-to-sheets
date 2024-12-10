# pdf_to_sheets/sheets_manager.py

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

class SheetsManager:
    def __init__(self, credentials_path):
        self.credentials_path = credentials_path
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.service = None
        self.drive_service = None
        self.share_email = self._load_share_email()  # Load share email from JSON
        self._authenticate()

    def _load_share_email(self):
        """Load the share email from the service account JSON file."""
        with open(self.credentials_path) as f:
            credentials_info = json.load(f)
            return credentials_info.get('share_email')

    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.scopes)
            self.service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            logging.info("Authentication successful")
        except Exception as e:
            logging.error(f"Authentication error: {str(e)}")

    def create_sheet(self, title):
        """Create a new Google Sheet and share it with the specified email"""
        try:
            # Create the spreadsheet
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet['spreadsheetId']
            logging.info(f"Spreadsheet created: {spreadsheet_id}")
            logging.info(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

            # Move the spreadsheet to the specified folder
            self.move_sheet_to_folder(spreadsheet_id, '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw')

            # Share the spreadsheet
            self.share_sheet(spreadsheet_id)
            return spreadsheet_id
        except Exception as e:
            logging.error(f"Error creating sheet: {str(e)}")
            return None

    def move_sheet_to_folder(self, spreadsheet_id, folder_id):
        """Move the created spreadsheet to the specified folder"""
        try:
            # Move the spreadsheet to the specified folder
            self.drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents='root',  # Remove from the root folder
                fields='id, parents'
            ).execute()
            logging.info(f"Spreadsheet moved to folder: {folder_id}")
        except Exception as e:
            logging.error(f"Error moving sheet to folder: {str(e)}")

    def share_sheet(self, spreadsheet_id):
        """Share the created spreadsheet with the specified email"""
        try:
            permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': self.share_email
            }
            self.drive_service.permissions().create(
                fileId=spreadsheet_id,
                body=permission
            ).execute()
            logging.info(f"Spreadsheet shared with {self.share_email}")
        except Exception as e:
            logging.error(f"Error sharing spreadsheet: {str(e)}")

    def append_patients_data(self, spreadsheet_id, patients):
        """Append extracted patient data to the Google Sheet."""
        try:
            # Prepare data for upload
            values = [[patient['name'], patient['time'], patient['type'], patient['provider'], patient['dob'], patient['phone']] for patient in patients]
            body = {
                'values': values
            }

            # Append data to the sheet
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='A1',  # Adjust range as needed
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            logging.info(f"Appended {result.get('updates').get('updatedCells')} cells")
            return True
        except Exception as e:
            logging.error(f"Error appending patient data: {str(e)}")
            return False

    def check_sheet_exists(self, spreadsheet_id):
        """Check if spreadsheet exists and is accessible"""
        try:
            self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            return True
        except Exception:
            return False

    def create_and_format_sheet(self, location, service_date, patients_data):
        """Create a new sheet with proper title format and column headers"""
        title = f"ART-{location} {service_date}"
        try:
            spreadsheet_id = self.create_sheet(title)
            if not spreadsheet_id:
                return None

            # Set up column headers
            headers = [
                "Name", "DOB", "Insurance", "Provider",
                "CPT1", "Mod/Units1",
                "CPT2", "Mod/Units2",
                "CPT3", "Mod/Units3",
                "CPT4", "Mod/Units4",
                "CPT5", "Mod/Units5"
            ]
            
            values = [headers]  # Start with headers
            values.extend(patients_data)  # Add patient data rows
            
            body = {'values': values}
            
            # Update the sheet with headers and data
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return spreadsheet_id
        except Exception as e:
            logging.error(f"Error creating and formatting sheet: {str(e)}")
            return None

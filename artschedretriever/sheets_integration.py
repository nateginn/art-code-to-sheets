# artschedretriever/sheets_integration.py

import json
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

class SheetsManager:
    def __init__(self, credentials_path):
        self.credentials_path = credentials_path
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.service = None
        self.drive_service = None
        self.share_email = self._load_share_email()
        self._authenticate()

    def _load_share_email(self):
        """Load the share email from the service account JSON file"""
        try:
            with open(self.credentials_path) as f:
                credentials_info = json.load(f)
                return credentials_info.get('share_email')
        except Exception as e:
            logging.error(f"Error loading share email: {str(e)}")
            return None

    def _authenticate(self):
        """Authenticate with Google Sheets and Drive APIs"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.scopes)
            self.service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            logging.info("Authentication successful")
        except Exception as e:
            logging.error(f"Authentication error: {str(e)}")
            raise

    def create_sheet(self, title):
        """Create a new Google Sheet"""
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet['spreadsheetId']
            
            # Share the sheet if email is available
            if self.share_email:
                self.share_sheet(spreadsheet_id)
                
            logging.info(f"Created spreadsheet: {spreadsheet_id}")
            return spreadsheet_id
        except Exception as e:
            logging.error(f"Error creating sheet: {str(e)}")
            return None

    def share_sheet(self, spreadsheet_id):
        """Share the sheet with the designated email"""
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
            logging.info(f"Sheet shared with {self.share_email}")
        except Exception as e:
            logging.error(f"Error sharing sheet: {str(e)}")

    def move_to_folder(self, spreadsheet_id, folder_id):
        """Move spreadsheet to specified folder"""
        try:
            file = self.drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents='root',
                fields='id, parents'
            ).execute()
            logging.info(f"Sheet moved to folder {folder_id}")
            return True
        except Exception as e:
            logging.error(f"Error moving sheet to folder: {str(e)}")
            return False

    def _clean_patient_name(self, name_string):
        """Extract just the name from the concatenated string"""
        return name_string.split('\n')[0].strip()

    def process_extracted_data(self, json_path):
        """Process data from the saved JSON file"""
        try:
            with open(json_path, 'r') as file:
                data = json.load(file)
            
            # Process patients directly without complex date handling
            processed_patients = []
            for patient in data['patients']:
                processed_patients.append([
                    self._clean_patient_name(patient['name']),
                    patient['birthday'],
                    patient['provider']
                ])
                
            # Get just the date portion from the service date string
            date_str = data['date_of_service'].split(' - ')[1]
            formatted_date = datetime.strptime(date_str, 'Thursday, %B %d, %Y').strftime('%m/%d/%y')
                
            return formatted_date, processed_patients
        except Exception as e:
            logging.error(f"Error processing JSON data: {str(e)}")
            return None, None

    def create_and_populate_sheet(self, location, json_path, folder_id):
        """Main method to create and populate sheet from extracted data"""
        try:
            # Process the data
            service_date, patients_data = self.process_extracted_data(json_path)
            if not service_date or not patients_data:
                return None

            # Create sheet with proper title
            sheet_title = f"ART-{location} {service_date}"
            spreadsheet_id = self.create_sheet(sheet_title)
            if not spreadsheet_id:
                return None

            # Move to proper folder
            if not self.move_to_folder(spreadsheet_id, folder_id):
                logging.error("Failed to move sheet to folder")
                return None

            # Set up headers and data
            headers = ["Name", "DOB", "Provider"]
            values = [headers] + patients_data

            # Update sheet with data
            try:
                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range='A1',
                    valueInputOption='RAW',
                    body={'values': values}
                ).execute()
                logging.info("Sheet populated with data successfully")
                return spreadsheet_id
            except Exception as e:
                logging.error(f"Error updating sheet values: {str(e)}")
                return None

        except Exception as e:
            logging.error(f"Error in create_and_populate_sheet: {str(e)}")
            return None

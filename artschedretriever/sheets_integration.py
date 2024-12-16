# artschedretriever/sheets_integration.py

import json
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_COLUMNS = [
    "Name",
    "DOB",
    "Insurance",
    "Provider",
    "CPT1",
    "Mod/Units1",
    "CPT2",
    "Mod/Units2",
    "CPT3",
    "Mod/Units3",
    "CPT4",
    "Mod/Units4",
    "CPT5",
    "Mod/Units5",
]


class SheetsManager:
    def __init__(self, credentials_path):
        self.credentials_path = credentials_path
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
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
                return credentials_info.get("share_email")
        except Exception as e:
            logging.error(f"Error loading share email: {str(e)}")
            return None

    def _authenticate(self):
        """Authenticate with Google Sheets and Drive APIs"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.scopes
            )
            self.service = build("sheets", "v4", credentials=credentials)
            self.drive_service = build("drive", "v3", credentials=credentials)
            logging.info("Authentication successful")
        except Exception as e:
            logging.error(f"Authentication error: {str(e)}")
            raise

    def create_sheet(self, title):
        """Create a new Google Sheet"""
        try:
            spreadsheet = {"properties": {"title": title}}
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet["spreadsheetId"]

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
                "type": "user",
                "role": "writer",
                "emailAddress": self.share_email,
            }
            self.drive_service.permissions().create(
                fileId=spreadsheet_id, body=permission
            ).execute()
            logging.info(f"Sheet shared with {self.share_email}")
        except Exception as e:
            logging.error(f"Error sharing sheet: {str(e)}")

    def move_to_folder(self, spreadsheet_id, folder_id):
        """Move spreadsheet to specified folder"""
        try:
            file = (
                self.drive_service.files()
                .update(
                    fileId=spreadsheet_id,
                    addParents=folder_id,
                    removeParents="root",
                    fields="id, parents",
                )
                .execute()
            )
            logging.info(f"Sheet moved to folder {folder_id}")
            return True
        except Exception as e:
            logging.error(f"Error moving sheet to folder: {str(e)}")
            return False

    def _clean_patient_name(self, name_string):
        """Extract just the name from the concatenated string"""
        return name_string.split("\n")[0].strip()

    def process_extracted_data(self, json_path):
        """Process data from the saved JSON file"""
        try:
            with open(json_path, 'r') as file:
                data = json.load(file)
            
            # Process date
            date_str = data['date_of_service'].split(' - ')[1]
            formatted_date = datetime.strptime(date_str, '%A, %B %d, %Y').strftime('%m/%d/%y')
            
            # Process patients
            processed_patients = []
            for patient in data.get('patients', []):
                patient_row = [
                    patient.get('name', '').split('\n')[0],  # Get first line of name
                    patient.get('birthday', ''),
                    '',  # Insurance placeholder
                    patient.get('provider', ''),
                    *[''] * 10  # Empty placeholders for CPT and Mod/Units columns
                ]
                processed_patients.append(patient_row)

            return formatted_date, processed_patients
        except Exception as e:
            logging.error(f"Error processing JSON data: {str(e)}")
            return None, None

    def create_and_populate_sheet(self, location, json_path, folder_id):
        """Create and populate sheet with extracted data using standardized format"""
        try:
            # Load JSON data
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Get date from service date
            date_str = data['date_of_service'].split(' - ')[1]
            service_date = datetime.strptime(date_str, '%A, %B %d, %Y').strftime('%m/%d/%y')
            
            # Create sheet
            sheet_title = f"ART-{location} {service_date}"
            spreadsheet_id = self.create_sheet(sheet_title)
            if not spreadsheet_id:
                return None

            # Move to folder
            if not self.move_to_folder(spreadsheet_id, folder_id):
                logging.error("Failed to move sheet to folder")
                return None

            # Prepare data
            values = [SHEET_COLUMNS]  # Headers
            for patient in data['patients']:
                row = [
                    patient['name'].split('\n')[0],  # Name (first line only)
                    patient['birthday'],              # DOB
                    '',                              # Insurance (empty initially)
                    patient['provider'],             # Provider
                    *[''] * 10                       # Empty CPT and Mod/Units columns
                ]
                values.append(row)

            # Update sheet
            try:
                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range='A1',
                    valueInputOption='RAW',
                    body={'values': values}
                ).execute()
                logging.info("Sheet populated with initial data")
                return spreadsheet_id
                
            except Exception as e:
                logging.error(f"Error updating sheet values: {str(e)}")
                return None

        except Exception as e:
            logging.error(f"Error in create_and_populate_sheet: {str(e)}")
            return None

    def extract_sheet_data(self, spreadsheet_id):
        """Extract all data from sheet including formatted columns"""
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range="A1:Z")
                .execute()
            )
            values = result.get("values", [])

            if not values:
                return []

            headers = values[0]
            data = []

            for row in values[1:]:  # Skip header row
                patient = {}
                for i, value in enumerate(row):
                    if i < len(headers):  # Ensure we have a header for this column
                        patient[headers[i]] = value
                data.append(patient)

            return data
        except Exception as e:
            logging.error(f"Error extracting sheet data: {str(e)}")
            return []

    def update_patient_data(self, spreadsheet_id, patient_data, row_index):
        """Update specific patient row with new data"""
        try:
            formatted_row = self.format_patient_data(patient_data)
            values = [[formatted_row[col] for col in SHEET_COLUMNS]]

            range_name = f"A{row_index + 2}:Z{row_index + 2}"  # +2 for header row and 1-based index

            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": values},
            ).execute()
            return True
        except Exception as e:
            logging.error(f"Error updating patient data: {str(e)}")
            return False

    def get_sheet_metadata(self, spreadsheet_id):
        """Get sheet title and other metadata"""
        try:
            metadata = (
                self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            return {
                "title": metadata["properties"]["title"],
                "locale": metadata["properties"].get("locale", "en_US"),
                "timeZone": metadata["properties"].get("timeZone", "America/Denver"),
            }
        except Exception as e:
            logging.error(f"Error getting sheet metadata: {str(e)}")
            return None

    def format_patient_data(self, patient_data):
        """Format patient data according to standardized column structure"""
        formatted_row = {col: "" for col in SHEET_COLUMNS}
        formatted_row.update(
            {
                "Name": patient_data.get("name", ""),
                "DOB": patient_data.get("dob", ""),
                "Provider": patient_data.get("provider", ""),
                "Insurance": patient_data.get("insurance", ""),
            }
        )

        # Process CPT entries if they exist
        entries = patient_data.get("entries", [])
        for i, entry in enumerate(entries, 1):
            if i > 5:  # Maximum 5 CPT entries
                break
            cpt_code = entry.get("cpt", "")
            mod_units = entry.get("mod_units", "")
            formatted_row[f"CPT{i}"] = cpt_code
            formatted_row[f"Mod/Units{i}"] = mod_units

        return formatted_row
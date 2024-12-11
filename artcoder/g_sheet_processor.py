from googleapiclient.discovery import build
import re
from datetime import datetime

class SheetsProcessor:
    def __init__(self, service):
        self.service = service
        self.schedule_date = None
        self.managed_columns = [
            'Name', 'DOB', 'Insurance', 'Provider',
            'CPT1', 'Mod/Units1', 'CPT2', 'Mod/Units2',
            'CPT3', 'Mod/Units3', 'CPT4', 'Mod/Units4',
            'CPT5', 'Mod/Units5'
        ]

    def get_existing_sheet_data(self, spreadsheet_id):
        """Get all existing data from sheet including formatting"""
        try:
            # Get sheet metadata
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id, 
                includeGridData=True
            ).execute()
            
            # Get the data values
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Sheet1'
            ).execute()
            
            return {
                'metadata': sheet_metadata,
                'values': result.get('values', [])
            }
        except Exception as e:
            print(f"Error getting sheet data: {str(e)}")
            return None

    def extract_patients(self, spreadsheet_id):
        """Extract patient information from the Google Sheet."""
        try:
            sheet_data = self.get_existing_sheet_data(spreadsheet_id)
            if not sheet_data or not sheet_data['values']:
                return [], None

            # Get sheet title and extract date
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            title = spreadsheet['properties']['title']
            self.extract_date_from_title(title)

            values = sheet_data['values']
            headers = values[0]

            # Map column indices
            col_indices = {
                header: idx for idx, header in enumerate(headers)
                if header in self.managed_columns
            }

            patients = []
            for row in values[1:]:  # Skip header row
                if len(row) > col_indices.get('Name', -1):
                    patient = {
                        'name': row[col_indices['Name']] if 'Name' in col_indices else '',
                        'dob': row[col_indices['DOB']] if 'DOB' in col_indices else '',
                        'insurance': row[col_indices['Insurance']] if 'Insurance' in col_indices else '',
                        'provider': row[col_indices['Provider']] if 'Provider' in col_indices else '',
                        'entries': []
                    }

                    # Extract CPT codes and Mod/Units
                    for i in range(1, 6):
                        cpt_col = f'CPT{i}'
                        mod_col = f'Mod/Units{i}'
                        if cpt_col in col_indices and mod_col in col_indices:
                            if len(row) > max(col_indices[cpt_col], col_indices[mod_col]):
                                cpt_code = row[col_indices[cpt_col]]
                                mod_units = row[col_indices[mod_col]]
                                if cpt_code or mod_units:  # Only add if either has data
                                    entry = f"CPT Code: {cpt_code}, Mod/Units: {mod_units}"
                                    patient['entries'].append(entry)

                    patients.append(patient)

            return patients, self.schedule_date

        except Exception as e:
            print(f"Error extracting patients: {str(e)}")
            return [], None

    def update_sheet_data(self, spreadsheet_id, patients_data):
        """Update existing sheet with new patient data while preserving formatting"""
        try:
            existing_data = self.get_existing_sheet_data(spreadsheet_id)
            if not existing_data:
                return False

            headers = existing_data['values'][0]
            col_indices = {
                header: idx for idx, header in enumerate(headers)
                if header in self.managed_columns
            }

            # Prepare updates maintaining existing data structure
            updates = []
            for patient in patients_data:
                row = [''] * len(headers)  # Initialize with empty values
                
                # Update only managed columns
                if 'Name' in col_indices:
                    row[col_indices['Name']] = patient['name']
                if 'DOB' in col_indices:
                    row[col_indices['DOB']] = patient['dob']
                if 'Insurance' in col_indices:
                    row[col_indices['Insurance']] = patient['insurance']
                if 'Provider' in col_indices:
                    row[col_indices['Provider']] = patient['provider']

                # Update CPT and Mod/Units columns
                for i, entry in enumerate(patient.get('entries', []), 1):
                    if i > 5:  # Limit to 5 entries
                        break
                    if 'CPT Code:' in entry and 'Mod/Units:' in entry:
                        cpt_code = entry.split('CPT Code:')[1].split(',')[0].strip()
                        mod_units = entry.split('Mod/Units:')[1].strip()
                        
                        cpt_col = f'CPT{i}'
                        mod_col = f'Mod/Units{i}'
                        if cpt_col in col_indices:
                            row[col_indices[cpt_col]] = cpt_code
                        if mod_col in col_indices:
                            row[col_indices[mod_col]] = mod_units

                updates.append(row)

            # Update the sheet
            body = {
                'values': updates
            }
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'Sheet1!A2:Z{len(updates)+1}',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            return True

        except Exception as e:
            print(f"Error updating sheet: {str(e)}")
            return False

    def extract_date_from_title(self, title):
        """Extract schedule date from sheet title."""
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YY or MM/DD/YYYY
            r'(\w+ \d{1,2}, \d{4})',       # Month DD, YYYY
        ]

        for pattern in date_patterns:
            date_match = re.search(pattern, title)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    for fmt in ['%m/%d/%y', '%m/%d/%Y', '%B %d, %Y']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            self.schedule_date = date_obj.strftime('%m/%d/%y')
                            return
                        except ValueError:
                            continue
                except Exception as e:
                    print(f"Error parsing date: {str(e)}")

        self.schedule_date = datetime.now().strftime('%m/%d/%y')

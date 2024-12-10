from googleapiclient.discovery import build
import re
from datetime import datetime

class SheetsProcessor:
    def __init__(self, service, gui):
        self.service = service
        self.schedule_date = None
        self.gui = gui  # Reference to the GUI for data population

    def extract_patients(self, spreadsheet_id):
        """Extract patient information from the Google Sheet."""
        try:
            # Get the sheet title to extract the schedule date
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            title = spreadsheet['properties']['title']
            self.extract_date_from_title(title)

            # Get the data from the first sheet
            result = self.service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range='Sheet1!A1:Z').execute()
            values = result.get('values', [])

            patients = []
            if not values:
                print("No data found in the sheet.")
                return patients, self.schedule_date

            # Process the data, assuming the first row contains headers
            for row in values[1:]:  # Skip header row
                if len(row) >= 4:  # Ensure there are enough columns
                    patient = {
                        'name': row[0],
                        'dob': row[1],
                        'insurance': row[2],  # Assuming insurance is in the third column
                        'provider': row[3],
                        'entries': []  # To store CPT codes and Mod/Units
                    }

                    # Populate entries for CPT codes and Mod/Units
                    for i in range(5):  # Assuming there are 5 CPT codes and Mod/Units
                        cpt_code = row[4 + (i * 2)] if len(row) > 4 + (i * 2) else ""
                        mod_units = row[5 + (i * 2)] if len(row) > 5 + (i * 2) else ""
                        if cpt_code or mod_units:  # Check if either is present
                            entry = f"CPT Code: {cpt_code}, Mod/Units: {mod_units}"
                            patient['entries'].append(entry)

                    patients.append(patient)  # Add patient to the list
            
            return patients, self.schedule_date  # Return both patients and the extracted DOS

        except Exception as e:
            print(f"Error extracting data from Google Sheet: {str(e)}")
            return [], None

    def extract_date_from_title(self, title):
        """Extract the schedule date from the sheet title."""
        # Match MM/DD/YY or MM/DD/YYYY format
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', title)  # Adjusted regex to match the date format
        if date_match:
            self.schedule_date = date_match.group(0)
        else:
            self.schedule_date = datetime.now().strftime('%m/%d/%y')  # Default to current date if not found

    def get_schedule_date(self):
        """Get the extracted schedule date."""
        return self.schedule_date

    def populate_gui(self, patients, title):
        """Populate the GUI fields with extracted patient data."""
        if patients:
            self.gui.patient_dob_edit.setText(self.extract_date_from_title(title))  # Set the DOS field
            self.gui.current_patient_index = 0
            self.load_next_patient_data(patients)

    def load_next_patient_data(self, patients):
        """Load the next patient's data into the form."""
        if patients and self.gui.current_patient_index < len(patients):
            patient = patients[self.gui.current_patient_index]
            self.gui.patient_name_edit.setText(patient['name'])
            self.gui.patient_dob_edit.setText(patient['dob'])
            self.gui.insurance_edit.clear()  # Clear insurance for user input
            self.gui.provider_edit.setText(patient['provider'])

            # Clear and restore entries for the new patient
            self.gui.entries_view.clear()
            for entry in patient['entries']:
                self.gui.entries_view.append(entry)

            self.gui.current_patient_index += 1
        else:
            print("No more patients to load.")

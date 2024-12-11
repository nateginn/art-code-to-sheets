import os
import sys
from datetime import datetime
import logging

from dotenv import load_dotenv
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QCompleter,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sheets_manager import SheetsManager
from g_sheet_processor import SheetsProcessor

LOCATIONS = ["Greeley", "UNC", "FOCO"]

# Common insurance providers (sorted alphabetically)
COMMON_INSURANCES = sorted(
    [
        "AUTO:GEICO",
        "AUTO:HSS",
        "AUTO:LIEN",
        "AUTO:MEDPAY",
        "AUTO:MARRICK",
        "AUTO:PROGRESSIVE",
        "AUTO:PROVE",
        "AUTO:STATE FARM",
        "AUTO:TRIO",
        "AUTO:USAA",
        "AETNA",
        "ANTHEM",
        "BCBS",
        "CIGNA",
        "CIGNA BEHAVIORAL",
        "COFINITY",
        "GOLDEN RULE",
        "HUMANA",
        "MEDICARE",
        "MEDICAID",
        "OPTUM",
        "OXFORD",
        "TRICARE",
        "UHC",
        "UHC COMMUNITY PLAN",
        "UHC MEDICARE SOLUTIONS",
        "UMR",
        "UNITED HEALTHCARE",
        "WORKER'S COMP",
    ]
)

# Common CPT codes (sorted numerically)
COMMON_CPT_CODES = sorted(
    [
        "97110",
        "97112",
        "97140",
        "97530",
        "97810",
        "97811",
        "97813",
        "97814",
        "98925",
        "98926",
        "98940",
        "98941",
        "98943",
        "99203",
        "99204",
        "99213",
        "99214",
    ]
)

# Common modifiers and units (sorted numerically)
COMMON_MODIFIERS = sorted(["1", "2", "3", "4", "25"])


class ConfirmationDialog(QtWidgets.QDialog):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.setWindowTitle("Confirmation")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(message))

        self.yes_button = QtWidgets.QPushButton("Yes")
        self.yes_button.clicked.connect(self.accept)
        layout.addWidget(self.yes_button)

        self.no_button = QtWidgets.QPushButton("No")
        self.no_button.clicked.connect(self.reject)
        layout.addWidget(self.no_button)

        self.setLayout(layout)

    def get_result(self):
        return self.result()


class PDFConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.extracted_data = []  # Store all extracted patient data
        self.current_patient_index = 0  # Track the current patient index
        self.patient_entries = {}  # Dictionary to store entries for each patient
        self.patient_insurance = {}  # Dictionary to store insurance for each patient
        self.export_button_clicked = False  # Track if export button has been clicked

        # Initialize sheets manager with credentials file
        credentials_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "service_account.json"
        )
        self.sheets_manager = SheetsManager(credentials_path)

        # Connect focus in event to set default value and select text
        self.mod_units_edit.focusInEvent = self.set_default_mod_units

    def set_default_mod_units(self, event):
        if not self.mod_units_edit.text():  # Check if the field is empty
            self.mod_units_edit.setText("1")  # Set default value to 1
            self.mod_units_edit.selectAll()  # Select the text to allow easy replacement
        super().focusInEvent(event)  # Call the base class method

    def init_ui(self):
        self.setWindowTitle("PDF Converter Tool")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Location Selection Section
        location_group = QGroupBox("Location")
        location_layout = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItems(LOCATIONS)
        location_layout.addWidget(self.location_combo)

        location_group.setLayout(location_layout)
        layout.addWidget(location_group)

        # Add DOS label and field back to the location section
        dos_label = QLabel("DOS:")
        self.dos_field = QLabel("")
        dos_layout = QHBoxLayout()
        dos_layout.addWidget(dos_label)
        dos_layout.addWidget(self.dos_field)
        location_layout.addLayout(dos_layout)  # Add DOS layout to location section

        # Extracted Data Section
        extracted_data_group = QGroupBox("Extracted Data")
        extracted_data_layout = QVBoxLayout()

        # Patient Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Patient Name:")
        self.patient_name_edit = QLineEdit()
        self.patient_name_edit.setPlaceholderText("Enter Patient Name")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.patient_name_edit)
        extracted_data_layout.addLayout(name_layout)

        # Patient DOB
        dob_layout = QHBoxLayout()
        dob_label = QLabel("Patient DOB:")
        self.patient_dob_edit = QLineEdit()
        self.patient_dob_edit.setPlaceholderText("Enter Patient DOB")
        dob_layout.addWidget(dob_label)
        dob_layout.addWidget(self.patient_dob_edit)
        extracted_data_layout.addLayout(dob_layout)

        # Provider
        provider_layout = QHBoxLayout()
        provider_label = QLabel("Provider:")
        self.provider_edit = QLineEdit()
        self.provider_edit.setPlaceholderText("Enter Provider Name")
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.provider_edit)
        extracted_data_layout.addLayout(provider_layout)

        # Insurance Input
        insurance_layout = QHBoxLayout()
        insurance_label = QLabel("Insurance:")
        self.insurance_edit = QLineEdit()
        self.insurance_edit.setPlaceholderText("Enter Insurance")
        completer = QCompleter(COMMON_INSURANCES)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.insurance_edit.setCompleter(completer)
        self.insurance_edit.textChanged.connect(self.on_insurance_changed)
        insurance_layout.addWidget(insurance_label)
        insurance_layout.addWidget(self.insurance_edit)
        extracted_data_layout.addLayout(insurance_layout)

        # CPT Code and Mod/Units Input (side by side)
        cpt_mod_layout = QHBoxLayout()
        cpt_label = QLabel("CPT Code:")
        self.cpt_code_edit = QLineEdit()
        self.cpt_code_edit.setPlaceholderText("Enter CPT Code")
        completer = QCompleter(COMMON_CPT_CODES)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.cpt_code_edit.setCompleter(completer)
        self.cpt_code_edit.setFixedWidth(100)
        self.cpt_code_edit.textChanged.connect(
            self.on_cpt_code_changed
        )  # Add text changed handler
        cpt_mod_layout.addWidget(cpt_label)
        cpt_mod_layout.addWidget(self.cpt_code_edit)

        mod_label = QLabel("Mod/Units:")
        self.mod_units_edit = QLineEdit()
        self.mod_units_edit.setPlaceholderText("Enter Mod/Units")
        self.mod_units_edit.setFixedWidth(100)
        cpt_mod_layout.addWidget(mod_label)
        cpt_mod_layout.addWidget(self.mod_units_edit)

        extracted_data_layout.addLayout(cpt_mod_layout)

        # Button to select PDF file
        self.select_file_button = QPushButton("Select PDF")
        self.select_file_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_file_button)

        # Add a label to display the selected file
        self.file_label = QLabel("Selected File: None")
        layout.addWidget(self.file_label)

        # Button to add entries to the viewbox
        self.add_entry_button = QPushButton("Add Entry")
        self.add_entry_button.clicked.connect(self.add_entry_to_viewbox)

        # Next Patient button
        self.next_patient_button = QPushButton("Next Patient")
        self.next_patient_button.clicked.connect(self.next_patient)

        # Previous Patient button
        self.prev_patient_button = QPushButton("Previous Patient")
        self.prev_patient_button.clicked.connect(self.prev_patient)

        # Export to Sheets button
        self.export_to_sheets_button = QPushButton("Export to Sheets")
        self.export_to_sheets_button.clicked.connect(self.export_to_sheets)

        # Button to load existing schedules
        self.load_schedules_button = QPushButton("Load Existing Schedule")
        self.load_schedules_button.clicked.connect(self.load_existing_schedule)
        layout.addWidget(self.load_schedules_button)

        # Create a horizontal layout for the buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_entry_button)
        button_layout.addWidget(self.next_patient_button)
        button_layout.addWidget(self.prev_patient_button)
        button_layout.addWidget(self.export_to_sheets_button)

        extracted_data_layout.addLayout(
            button_layout
        )  # Add button layout to extracted data

        # Ensure Enter key activates the Add Entry button
        self.add_entry_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.add_entry_button.keyPressEvent = lambda event: (
            self.add_entry_to_viewbox()
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            else None
        )

        # Ensure Enter key activates the Add Entry button from the QLineEdit fields
        self.cpt_code_edit.returnPressed.connect(
            self.mod_units_edit.setFocus
        )  # Move to Mod/Units field
        self.mod_units_edit.returnPressed.connect(self.add_entry_to_viewbox)

        # Ensure Enter key activates the Next Patient button
        self.next_patient_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.next_patient_button.keyPressEvent = lambda event: (
            self.next_patient()
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            else None
        )

        # Ensure Enter key activates the Previous Patient button
        self.prev_patient_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.prev_patient_button.keyPressEvent = lambda event: (
            self.prev_patient()
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            else None
        )

        # Ensure Enter key activates the Export to Sheets button
        self.export_to_sheets_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.export_to_sheets_button.keyPressEvent = lambda event: (
            self.export_to_sheets()
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            else None
        )

        # Viewbox for Entries
        self.entries_view = QTextEdit()
        self.entries_view.setReadOnly(True)
        self.entries_view.mouseMoveEvent = self.on_viewbox_mouse_move
        self.entries_view.mousePressEvent = self.on_viewbox_click
        self.entries_view.leaveEvent = self.on_viewbox_leave
        extracted_data_layout.addWidget(self.entries_view)

        extracted_data_group.setLayout(extracted_data_layout)
        layout.addWidget(extracted_data_group)

        # Add a label to display the status of PDF processing
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Status/Counter Label
        self.status_counter_label = QLabel("0/0")  # Initialize with 0 completed patients
        layout.addWidget(self.status_counter_label)

        # Set main layout
        self.setLayout(layout)
        self.setMinimumWidth(150)
        self.setMinimumHeight(150)

    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            "C:/Users/nginn/OneDrive/Documents/PF_Schedules",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if file_name:
            self.file_label.setText(f"Selected File: {file_name}")
            self.pdf_path = file_name
            self.process_pdf()

    def process_pdf(self):
        """Process the selected PDF file"""
        try:
            from pdf_processor import PDFProcessor

            processor = PDFProcessor()

            # Process the PDF and get the data
            self.extracted_data = processor.extract_patients(self.pdf_path)

            if not self.extracted_data:
                print("No data extracted from PDF")
                return

            # Get and display the schedule date
            schedule_date = processor.get_schedule_date()
            self.dos_field.setText(schedule_date)  # Update the DOS field

            # Load the first patient's data
            self.current_patient_index = 0
            self.load_next_patient_data()
            self.insurance_edit.setFocus()  # Set focus to insurance field after PDF processing
        except Exception as e:
            print("Error processing PDF:", str(e))

    def add_entry_to_viewbox(self):
        cpt_code = self.cpt_code_edit.text().strip()
        mod_units = self.mod_units_edit.text().strip()

        # Validation check for CPT code
        if not cpt_code or len(cpt_code) != 5:
            self.status_label.setText("Error: CPT Code must be a 5-digit code.")
            self.cpt_code_edit.setFocus()
            return

        # Check if the CPT code is in the list
        if cpt_code not in COMMON_CPT_CODES:
            self.status_label.setText("Error: CPT Code does not match any in the list.")
            self.cpt_code_edit.setFocus()
            return

        # Validation check for Mod/Units
        if not mod_units:
            self.status_label.setText("Error: Mod/Units cannot be left empty.")
            self.mod_units_edit.setFocus()
            return

        # If the code is valid, proceed to add the entry
        entry = f"CPT Code: {cpt_code}, Mod/Units: {mod_units}"
        self.entries_view.append(entry)

        # Store the entry for the current patient
        current_patient = self.patient_name_edit.text()
        if current_patient not in self.patient_entries:
            self.patient_entries[current_patient] = []
        self.patient_entries[current_patient].append(entry)

        self.cpt_code_edit.clear()
        self.mod_units_edit.clear()
        self.cpt_code_edit.setFocus()  # Set focus back to the CPT Code field

        # Update the status counter
        self.update_status_counter()

    def next_patient(self):
        """Move to the next patient"""
        # Check if insurance is selected
        current_patient = self.patient_name_edit.text()
        current_insurance = self.insurance_edit.text()

        if not current_insurance:
            self.status_label.setText("Error: Insurance must be selected before moving to next patient")
            self.insurance_edit.setFocus()
            return

        # Save the current insurance
        self.patient_insurance[current_patient] = current_insurance

        if self.current_patient_index < len(self.extracted_data) - 1:
            self.load_next_patient_data()
            self.insurance_edit.setFocus()  # Set focus to insurance field
        else:
            self.status_label.setText("No more patients to process")

    def prev_patient(self):
        """Move to the previous patient"""
        if self.current_patient_index > 1:  # We can go back
            self.current_patient_index -= (
                2  # Subtract 2 because load_next_patient_data will add 1
            )
            self.load_next_patient_data()
            self.insurance_edit.setFocus()  # Set focus to insurance field
        else:
            print("Already at the first patient")

    def load_next_patient_data(self):
        """Load the next patient's data into the form"""
        if self.extracted_data and self.current_patient_index < len(
            self.extracted_data
        ):
            # Save current patient's data before loading next patient
            current_patient = self.patient_name_edit.text()
            if current_patient:
                entries_text = self.entries_view.toPlainText().strip()
                if entries_text:
                    self.patient_entries[current_patient] = entries_text.split("\n")
                self.patient_insurance[current_patient] = self.insurance_edit.text()

            patient = self.extracted_data[self.current_patient_index]
            patient_name = patient["name"]
            self.patient_name_edit.setText(patient_name)
            self.patient_dob_edit.setText(patient["dob"])
            self.provider_edit.setText(patient["provider"])

            # Restore insurance if previously saved, otherwise use default
            self.insurance_edit.setText(
                self.patient_insurance.get(patient_name, patient.get("insurance", ""))
            )
            self.cpt_code_edit.clear()
            self.mod_units_edit.clear()

            # Clear and restore entries for the new patient
            self.entries_view.clear()
            if patient_name in self.patient_entries:
                for entry in self.patient_entries[patient_name]:
                    self.entries_view.append(entry)

            self.current_patient_index += 1
        else:
            print("No more patients to load.")

    def on_cpt_code_changed(self, text):
        """Handle CPT code changes"""
        if text.startswith("99"):
            self.mod_units_edit.setText("25")

    def on_insurance_changed(self, insurance):
        """Handle insurance selection"""
        if insurance:  # Only save if insurance is not empty
            current_patient = self.patient_name_edit.text()
            self.patient_insurance[current_patient] = insurance
            self.status_label.setText("")  # Clear any error message

    def on_viewbox_mouse_move(self, event):
        """Highlight the line under the mouse cursor"""
        cursor = self.entries_view.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)

        # Remove all highlights first
        cursor_all = QTextCursor(self.entries_view.document())
        cursor_all.select(QTextCursor.SelectionType.Document)
        format_normal = QTextCharFormat()
        cursor_all.setCharFormat(format_normal)

        # Add highlight to current line
        format_new = QTextCharFormat()
        format_new.setFontWeight(700)  # Bold
        cursor.setCharFormat(format_new)

    def on_viewbox_leave(self, event):
        """Remove highlight when mouse leaves the viewbox"""
        cursor_all = QTextCursor(self.entries_view.document())
        cursor_all.select(QTextCursor.SelectionType.Document)
        format_normal = QTextCharFormat()
        cursor_all.setCharFormat(format_normal)

    def on_viewbox_click(self, event):
        """Handle single click on viewbox"""
        cursor = self.entries_view.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line = cursor.selectedText()

        # Extract CPT code and Mod/Units from the line
        import re

        match = re.match(r"CPT Code: (.*?), Mod/Units: (.*)", line)
        if match:
            cpt_code = match.group(1)
            mod_units = match.group(2)
            # Put the values back in the input fields
            self.cpt_code_edit.setText(cpt_code)
            self.mod_units_edit.setText(mod_units)
            # Remove the line from viewbox and update patient entries
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # Remove the newline

            # Update stored entries for current patient
            current_patient = self.patient_name_edit.text()
            if current_patient in self.patient_entries:
                self.patient_entries[current_patient] = (
                    self.entries_view.toPlainText().split("\n")
                )
                if "" in self.patient_entries[current_patient]:
                    self.patient_entries[current_patient].remove("")

    def export_to_sheets(self):
        if self.export_button_clicked:
            return
        
        try:
            # Get the location from the combo box
            location = self.location_combo.currentText()
            # Get the service date from the DOS field
            service_date = self.dos_field.text()
            
            if not location or not service_date:
                self.status_label.setText("Error: Missing location or service date")
                return

            all_patient_data = []
            
            # Rest of your existing export code...
            for patient in self.extracted_data:
                patient_name = patient["name"]
                patient_dob = patient.get("dob", "")
                patient_insurance = self.patient_insurance.get(patient_name, "")
                patient_provider = patient.get("provider", "")
                
                # Initialize a row with values for all columns
                patient_row = [patient_name, patient_dob, patient_insurance, patient_provider, "", "", "", "", "", "", "", "", "", "", "", "", "", ""]

                # Fill in the CPT codes and Mod/Units if available
                entries = self.patient_entries.get(patient_name, [])
                for i, entry in enumerate(entries[:5]):  # Limit to 5 CPT codes
                    if "CPT Code:" in entry:
                        cpt_code = entry.split("CPT Code: ")[1].split(",")[0].strip()
                        mod_units = entry.split("Mod/Units: ")[1].strip()
                        # CPT codes start at index 4 and increment by 2
                        patient_row[4 + (i * 2)] = cpt_code
                        patient_row[5 + (i * 2)] = mod_units
                
                all_patient_data.append(patient_row)

            # Create and format the sheet with the correct title and data
            spreadsheet_id = self.sheets_manager.create_and_format_sheet(
                location, service_date, all_patient_data
            )

            if spreadsheet_id:
                self.status_label.setText("Successfully exported to Google Sheets")
                self.export_button_clicked = True  # Prevent multiple exports
                # Close the application after a successful export
                self.close()
            else:
                self.status_label.setText("Failed to export to Google Sheets")
                
        except Exception as e:
            self.status_label.setText(f"Error exporting to sheets: {str(e)}")
            logging.error(f"Export error: {str(e)}")

    def update_status_counter(self):
        """Update the status counter for completed patients"""
        completed_patients = 0
        total_patients = len(self.extracted_data)

        for patient_name in self.patient_entries:
            if self.patient_insurance.get(patient_name) and any("CPT Code:" in entry for entry in self.patient_entries[patient_name]):
                completed_patients += 1

        self.status_counter_label.setText(f"{completed_patients}/{total_patients}")

    def load_existing_schedule(self):
        """Load data from an existing Google Sheet in the specified folder"""
        try:
            folder_id = '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw'
            results = self.sheets_manager.drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
                fields="files(id, name)"
            ).execute()
            files = results.get('files', [])

            if not files:
                self.status_label.setText("No sheets found in the specified folder.")
                return

            sheet_names = [file['name'] for file in files]
            selected_sheet, ok = QtWidgets.QInputDialog.getItem(self, "Select Sheet", "Choose a sheet:", sheet_names, 0, False)

            if ok and selected_sheet:
                selected_file = next(file for file in files if file['name'] == selected_sheet)
                sheet_id = selected_file['id']

                # Create an instance of SheetsProcessor and extract data
                sheets_processor = SheetsProcessor(self.sheets_manager.service, self)
                patients, dos = sheets_processor.extract_patients(sheet_id)

                # Populate the DOS field in the GUI
                self.dos_field.setText(dos)  # Set the DOS field with the extracted date

                # Populate the GUI with extracted patient data
                self.populate_gui_with_patients(patients)

        except Exception as e:
            self.status_label.setText(f"Error loading schedule: {str(e)}")
            logging.error(f"Error loading schedule: {str(e)}")

    def populate_gui_with_patients(self, patients):
        """Populate the GUI fields with extracted patient data"""
        if patients:
            self.current_patient_index = 0
            self.extracted_data = patients  # Store extracted data for navigation
            self.load_next_patient_data()  # Load the first patient's data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFConverterApp()
    window.show()
    sys.exit(app.exec())

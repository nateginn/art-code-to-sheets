# artschedretriever/gui.py

import os
import sys
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit,
    QGroupBox, QMessageBox, QCompleter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCharFormat, QTextCursor

from sheets_integration import SheetsManager

LOCATIONS = ["Greeley", "UNC", "FOCO"]

COMMON_INSURANCES = sorted([
    "AUTO:GEICO", "AUTO:HSS", "AUTO:LIEN", "AUTO:MEDPAY", "AUTO:MARRICK",
    "AUTO:PROGRESSIVE", "AUTO:PROVE", "AUTO:STATE FARM", "AUTO:TRIO", "AUTO:USAA",
    "AETNA", "ANTHEM", "BCBS", "CIGNA", "CIGNA BEHAVIORAL", "COFINITY",
    "GOLDEN RULE", "HUMANA", "MEDICARE", "MEDICAID", "OPTUM", "OXFORD",
    "TRICARE", "UHC", "UHC COMMUNITY PLAN", "UHC MEDICARE SOLUTIONS",
    "UMR", "UNITED HEALTHCARE", "WORKER'S COMP"
])

COMMON_CPT_CODES = sorted([
    "97110", "97112", "97140", "97530", "97810", "97811",
    "97813", "97814", "98925", "98926", "98940", "98941",
    "98943", "99203", "99204", "99213", "99214"
])

class SheetManagementGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.credentials_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'service_account.json'
        )
        self.sheets_manager = SheetsManager(self.credentials_path)
        self.current_patient_index = 0
        self.patient_entries = {}
        self.patient_insurance = {}
        self.extracted_data = []
        self.init_ui()
        # Add focus event handler for mod_units
        self.mod_units_edit.focusInEvent = self.set_default_mod_units

    def set_default_mod_units(self, event):
        if not self.mod_units_edit.text():
            self.mod_units_edit.setText("1")
            self.mod_units_edit.selectAll()

    def init_ui(self):
        self.setWindowTitle("Sheet Management Tool")
        layout = QVBoxLayout()
        
        # Location Selection
        location_group = QGroupBox("Location")
        location_layout = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItems(LOCATIONS)
        location_layout.addWidget(self.location_combo)
        
        # DOS Field
        dos_label = QLabel("DOS:")
        self.dos_field = QLabel("")
        dos_layout = QHBoxLayout()
        dos_layout.addWidget(dos_label)
        dos_layout.addWidget(self.dos_field)
        location_layout.addLayout(dos_layout)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)

        # Add Load Schedule button here, after location group
        self.load_button = QPushButton("Load Schedule")
        self.load_button.clicked.connect(self.load_existing_schedule)
        layout.addWidget(self.load_button)

        # Patient Data Section
        data_group = QGroupBox("Patient Data")
        data_layout = QVBoxLayout()

        # Patient Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Patient Name:")
        self.patient_name_edit = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.patient_name_edit)
        data_layout.addLayout(name_layout)

        # Patient DOB
        dob_layout = QHBoxLayout()
        dob_label = QLabel("Patient DOB:")
        self.patient_dob_edit = QLineEdit()
        dob_layout.addWidget(dob_label)
        dob_layout.addWidget(self.patient_dob_edit)
        data_layout.addLayout(dob_layout)

        # Provider
        provider_layout = QHBoxLayout()
        provider_label = QLabel("Provider:")
        self.provider_edit = QLineEdit()
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.provider_edit)
        data_layout.addLayout(provider_layout)

        # Insurance with Autocomplete
        insurance_layout = QHBoxLayout()
        insurance_label = QLabel("Insurance:")
        self.insurance_edit = QLineEdit()
        completer = QCompleter(COMMON_INSURANCES)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.insurance_edit.setCompleter(completer)
        insurance_layout.addWidget(insurance_label)
        insurance_layout.addWidget(self.insurance_edit)
        data_layout.addLayout(insurance_layout)

        # CPT and Mod/Units
        cpt_mod_layout = QHBoxLayout()
        
        cpt_label = QLabel("CPT Code:")
        self.cpt_code_edit = QLineEdit()
        self.cpt_code_edit.setFixedWidth(100)
        cpt_completer = QCompleter(COMMON_CPT_CODES)
        cpt_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.cpt_code_edit.setCompleter(cpt_completer)
        
        mod_label = QLabel("Mod/Units:")
        self.mod_units_edit = QLineEdit()
        self.mod_units_edit.setFixedWidth(100)
        
        cpt_mod_layout.addWidget(cpt_label)
        cpt_mod_layout.addWidget(self.cpt_code_edit)
        cpt_mod_layout.addWidget(mod_label)
        cpt_mod_layout.addWidget(self.mod_units_edit)
        
        data_layout.addLayout(cpt_mod_layout)

        # Control Buttons
        button_layout = QHBoxLayout()
        
        self.add_entry_button = QPushButton("Add Entry")
        self.add_entry_button.clicked.connect(self.add_entry_to_viewbox)

        self.next_button = QPushButton("Next Patient")
        self.next_button.clicked.connect(self.next_patient)

        self.prev_button = QPushButton("Previous Patient")
        self.prev_button.clicked.connect(self.prev_patient)

        button_layout.addWidget(self.add_entry_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.prev_button)

        data_layout.addLayout(button_layout)

        # Add keyboard activation for buttons
        for button in [self.load_button, self.add_entry_button, self.prev_button, 
                       self.next_button]:
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.keyPressEvent = lambda event, btn=button: (
                btn.click() if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) 
                else None
            )

        # Add field navigation
        self.cpt_code_edit.returnPressed.connect(self.mod_units_edit.setFocus)
        self.mod_units_edit.returnPressed.connect(self.validate_and_add_entry)

        # Entries View
        self.entries_view = QTextEdit()
        self.entries_view.setReadOnly(True)
        self.entries_view.mousePressEvent = self.on_viewbox_click
        self.entries_view.mouseMoveEvent = self.on_viewbox_mouse_move
        self.entries_view.leaveEvent = self.on_viewbox_leave
        data_layout.addWidget(self.entries_view)

        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # Status Labels
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.counter_label = QLabel("0/0")
        layout.addWidget(self.counter_label)

        # Create and add save button
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_changes)

        # Create close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_application)
        self.close_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.close_button.keyPressEvent = lambda event: (
            self.close_application() if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) 
            else None
        )

        # Modify bottom button layout to push close button right
        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addWidget(self.save_button)
        bottom_button_layout.addStretch()  # This pushes the close button to the right
        bottom_button_layout.addWidget(self.close_button)

        layout.addLayout(bottom_button_layout)

        # Add focus highlighting style
        focus_style = """
        QLineEdit:focus {
            background-color: #FFFFD4;  /* Very light yellow */
        }
        """

        # Apply style to input fields
        self.cpt_code_edit.setStyleSheet(focus_style)
        self.mod_units_edit.setStyleSheet(focus_style)
        self.insurance_edit.setStyleSheet(focus_style)
        self.patient_name_edit.setStyleSheet(focus_style)
        self.patient_dob_edit.setStyleSheet(focus_style)
        self.provider_edit.setStyleSheet(focus_style)

        # Prevent viewbox from being part of tab order
        self.entries_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setLayout(layout)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

    def load_existing_schedule(self):
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

            # Show sheet selection dialog
            from PyQt6.QtWidgets import QInputDialog
            sheet_names = [file['name'] for file in files]
            selected_sheet, ok = QInputDialog.getItem(
                self, "Select Sheet", "Choose a sheet:", sheet_names, 0, False
            )

            if ok and selected_sheet:
                selected_file = next(file for file in files if file['name'] == selected_sheet)
                sheet_id = selected_file['id']
                
                # Extract date from sheet title
                if "ART-" in selected_sheet:
                    self.dos_field.setText(selected_sheet.split(" ")[-1])

                # Load sheet data using new method
                self.extracted_data = self.sheets_manager.extract_sheet_data(sheet_id)
                
                if not self.extracted_data:
                    self.status_label.setText("No data found in sheet")
                    return

                self.current_patient_index = 0
                self.load_current_patient()
                self.update_counter()
                    
        except Exception as e:
            self.status_label.setText(f"Error loading schedule: {str(e)}")
            logging.error(f"Error loading schedule: {str(e)}")

    def load_current_patient(self):
        if not self.extracted_data or self.current_patient_index >= len(self.extracted_data):
            return

        patient = self.extracted_data[self.current_patient_index]
        
        self.patient_name_edit.setText(patient.get('Name', ''))
        self.patient_dob_edit.setText(patient.get('DOB', ''))
        self.provider_edit.setText(patient.get('Provider', ''))
        self.insurance_edit.setText(patient.get('Insurance', ''))
        
        # Clear existing entries
        self.entries_view.clear()
        
        # Load CPT codes and Mod/Units
        for i in range(1, 6):
            cpt = patient.get(f'CPT{i}', '')
            mod = patient.get(f'Mod/Units{i}', '')
            if cpt or mod:
                self.entries_view.append(f"CPT Code: {cpt}, Mod/Units: {mod}")

    def check_duplicate_cpt(self, cpt_code):
        entries_text = self.entries_view.toPlainText()
        entries = entries_text.split('\n') if entries_text else []
        
        for entry in entries:
            if entry and 'CPT Code:' in entry:
                existing_cpt = entry.split('CPT Code:')[1].split(',')[0].strip()
                if existing_cpt == cpt_code:
                    return True
        return False

    def validate_fields(self):
        cpt_code = self.cpt_code_edit.text().strip()
        mod_units = self.mod_units_edit.text().strip()
        insurance = self.insurance_edit.text().strip()

        if insurance and insurance not in COMMON_INSURANCES:
            self.status_label.setText("Error: Insurance must be from the predefined list")
            self.insurance_edit.setFocus()
            return False

        if not cpt_code or len(cpt_code) != 5:
            self.status_label.setText("Error: CPT Code must be a 5-digit code")
            self.cpt_code_edit.setFocus()
            return False

        if cpt_code not in COMMON_CPT_CODES:
            self.status_label.setText("Error: CPT Code must be from the predefined list")
            self.cpt_code_edit.setFocus()
            return False

        if self.check_duplicate_cpt(cpt_code):
            self.status_label.setText("Error: This CPT code is already entered. Select the code in the viewbox to modify.")
            self.cpt_code_edit.setFocus()
            return False

        if not mod_units:
            self.status_label.setText("Error: Mod/Units required")
            self.mod_units_edit.setFocus()
            return False

        self.status_label.setText("")
        return True

    def add_entry_to_viewbox(self):
        if not self.validate_fields():
            return

        cpt_code = self.cpt_code_edit.text().strip()
        mod_units = self.mod_units_edit.text().strip()
        
        entry = f"CPT Code: {cpt_code}, Mod/Units: {mod_units}"
        self.entries_view.append(entry)
        
        current_patient = self.patient_name_edit.text()
        if current_patient not in self.patient_entries:
            self.patient_entries[current_patient] = []
        self.patient_entries[current_patient].append(entry)

        self.cpt_code_edit.clear()
        self.mod_units_edit.clear()
        self.cpt_code_edit.setFocus()

    def prev_patient(self):
        if self.current_patient_index > 0:
            self.save_current_patient_state()
            self.current_patient_index -= 1
            self.load_current_patient()
            self.update_counter()

    def next_patient(self):
        current_insurance = self.insurance_edit.text().strip()
        
        if current_insurance and current_insurance not in COMMON_INSURANCES:
            self.status_label.setText("Error: Insurance must be from the predefined list")
            self.insurance_edit.setFocus()
            return
        
        if self.current_patient_index < len(self.extracted_data) - 1:
            self.save_current_patient_state()
            self.current_patient_index += 1
            self.load_current_patient()
            self.update_counter()
            self.insurance_edit.setFocus()

    def save_current_patient_state(self):
        current_patient = self.patient_name_edit.text()
        if current_patient:
            self.patient_insurance[current_patient] = self.insurance_edit.text()
            entries = self.entries_view.toPlainText().strip()
            if entries:
                self.patient_entries[current_patient] = entries.split('\n')
            elif current_patient in self.patient_entries:
                # Clear entries if viewbox is empty
                self.patient_entries[current_patient] = []

    def save_changes(self):
        try:
            # Save current patient's state before proceeding
            self.save_current_patient_state()
            
            # Get current sheet ID
            folder_id = '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw'
            location = self.location_combo.currentText()
            service_date = self.dos_field.text()
            sheet_title = f"ART-{location} {service_date}"
            
            results = self.sheets_manager.drive_service.files().list(
                q=f"'{folder_id}' in parents and name='{sheet_title}'",
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                self.status_label.setText("Error: Could not find original sheet")
                return
            
            spreadsheet_id = files[0]['id']
            
            # Update each patient's data
            for index, patient in enumerate(self.extracted_data):
                if patient['Name'] in self.patient_entries or patient['Name'] in self.patient_insurance:
                    patient_data = {
                        'name': patient['Name'],
                        'dob': patient['DOB'],
                        'provider': patient['Provider'],
                        'insurance': self.patient_insurance.get(patient['Name'], patient.get('Insurance', '')),
                        'entries': []
                    }
                    
                    # Add entries if they exist
                    if patient['Name'] in self.patient_entries:
                        for entry in self.patient_entries[patient['Name']]:
                            if 'CPT Code:' in entry and 'Mod/Units:' in entry:
                                cpt = entry.split('CPT Code:')[1].split(',')[0].strip()
                                mod = entry.split('Mod/Units:')[1].strip()
                                patient_data['entries'].append({'cpt': cpt, 'mod_units': mod})
                    
                    # Update the patient data
                    self.sheets_manager.update_patient_data(spreadsheet_id, patient_data, index)
            
            self.status_label.setText("Changes saved successfully")
            
        except Exception as e:
            self.status_label.setText(f"Error saving changes: {str(e)}")
            logging.error(f"Error saving changes: {str(e)}")

    def on_viewbox_click(self, event):
        cursor = self.entries_view.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line = cursor.selectedText()

        import re
        match = re.match(r"CPT Code: (.*?), Mod/Units: (.*)", line)
        if match:
            cpt_code = match.group(1)
            mod_units = match.group(2)
            
            # Clear fields before setting new values
            self.cpt_code_edit.clear()
            self.mod_units_edit.clear()
            
            # Set new values
            self.cpt_code_edit.setText(cpt_code)
            self.mod_units_edit.setText(mod_units)
            
            # Remove the line from viewbox and update patient entries
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # Remove the newline

            # Update stored entries for current patient
            current_patient = self.patient_name_edit.text()
            if current_patient in self.patient_entries:
                self.patient_entries[current_patient] = self.entries_view.toPlainText().split("\n")
                if "" in self.patient_entries[current_patient]:
                    self.patient_entries[current_patient].remove("")
            
            # Set focus to CPT field
            self.cpt_code_edit.setFocus()

    def on_viewbox_mouse_move(self, event):
        cursor = self.entries_view.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        
        # Remove existing formatting
        cursor_all = QTextCursor(self.entries_view.document())
        cursor_all.select(QTextCursor.SelectionType.Document)
        format_normal = QTextCharFormat()
        cursor_all.setCharFormat(format_normal)
        
        # Add hover format
        format_hover = QTextCharFormat()
        format_hover.setFontWeight(700)  # Bold
        format_hover.setFontUnderline(True)  # Underline
        cursor.setCharFormat(format_hover)

    def on_viewbox_leave(self, event):
        cursor = QTextCursor(self.entries_view.document())
        cursor.select(QTextCursor.SelectionType.Document)
        format_normal = QTextCharFormat()
        cursor.setCharFormat(format_normal)

    def update_counter(self):
        """Update the status counter display"""
        if self.extracted_data:
            self.counter_label.setText(f"{self.current_patient_index + 1}/{len(self.extracted_data)}")

    def validate_and_add_entry(self):
        if not self.mod_units_edit.text().strip():
            self.status_label.setText("Error: Mod/Units required")
            self.mod_units_edit.setFocus()
            return
        self.add_entry_to_viewbox()
        self.cpt_code_edit.setFocus()

    def close_application(self):
        reply = QMessageBox.question(
            self, 
            'Confirm Exit',
            'Would you like to save changes before closing?',
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No | 
            QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Save changes first
            self.save_changes()
            self.close()
            QApplication.quit()
        elif reply == QMessageBox.StandardButton.No:
            # Close without saving
            self.close()
            QApplication.quit()
        # If Cancel, do nothing and return to application

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = SheetManagementGUI()
    window.show()
    sys.exit(app.exec())

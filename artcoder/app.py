import sys
from datetime import datetime
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCompleter,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QTextEdit,
)

LOCATIONS = ["Greeley", "UNC", "FOCO"]
INSURANCES = ["AETNA", "BCBS", "CIGNA", "MEDICARE", "UHC"]

class PDFConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.extracted_data = {}  # Initialize extracted_data as a dictionary

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

        # CPT Code and Mod/Units Input (side by side)
        cpt_mod_layout = QHBoxLayout()
        cpt_label = QLabel("CPT Code:")
        self.cpt_code_edit = QLineEdit()
        self.cpt_code_edit.setPlaceholderText("Enter CPT Code")
        self.cpt_code_edit.setFixedWidth(100)
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
        extracted_data_layout.addWidget(self.add_entry_button)

        # Next Patient button
        self.next_patient_button = QPushButton("Next Patient")
        self.next_patient_button.clicked.connect(self.next_patient)
        extracted_data_layout.addWidget(self.next_patient_button)

        # Ensure Enter key activates the Add Entry button
        self.add_entry_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.add_entry_button.keyPressEvent = lambda event: self.add_entry_to_viewbox() if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) else None

        # Ensure Enter key activates the Add Entry button from the QLineEdit fields
        self.cpt_code_edit.returnPressed.connect(self.add_entry_to_viewbox)
        self.mod_units_edit.returnPressed.connect(self.add_entry_to_viewbox)

        # Viewbox for Entries
        self.entries_view = QTextEdit()
        self.entries_view.setReadOnly(True)
        extracted_data_layout.addWidget(self.entries_view)

        extracted_data_group.setLayout(extracted_data_layout)
        layout.addWidget(extracted_data_group)

        # Add a label to display the status of PDF processing
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Set main layout
        self.setLayout(layout)
        self.setMinimumWidth(150)
        self.setMinimumHeight(200)

    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Select PDF File", 
            "C:/Users/nginn/OneDrive/Documents/PF_Schedules",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if file_name:
            self.file_label.setText(f"Selected File: {file_name}")
            self.pdf_path = file_name
            self.process_pdf()

    def process_pdf(self):
        from pdf_processor import PDFProcessor
        
        processor = PDFProcessor()
        patients = processor.extract_patients(self.pdf_path)
        
        if patients and len(patients) > 0:
            patient = patients[0]  # Get first patient
            self.patient_name_edit.setText(patient['name'])
            self.patient_dob_edit.setText(patient['dob'])
            self.provider_edit.setText(patient['provider'])
            
            # Format and store schedule date
            if processor.schedule_date:
                date_obj = datetime.strptime(processor.schedule_date, '%B %d, %Y')
                formatted_date = date_obj.strftime('%m/%d/%y')
                self.extracted_data['schedule_date'] = formatted_date
                self.dos_field.setText(formatted_date)  # Update DOS field with schedule date
            
            self.status_label.setText("PDF processed successfully")
            self.extracted_data = patient

    def add_entry_to_viewbox(self):
        cpt_code = self.cpt_code_edit.text().strip()
        mod_units = self.mod_units_edit.text().strip()
        if cpt_code and mod_units:
            self.entries_view.append(f"CPT Code: {cpt_code}, Mod/Units: {mod_units}")
            self.cpt_code_edit.clear()
            self.mod_units_edit.clear()
            self.cpt_code_edit.setFocus()  # Set focus back to the CPT Code field

    def next_patient(self):
        # Here you would save the current entries to a data structure or file
        current_entries = self.entries_view.toPlainText()
        print("Saving entries for the current patient:", current_entries)

        # Load next patient's data (this is a placeholder)
        self.load_next_patient_data()

        # Set focus back to the CPT Code field
        self.cpt_code_edit.setFocus()

    def load_next_patient_data(self):
        # Placeholder for loading the next patient's data
        self.patient_name_edit.setText("Next Patient Name")  # Example
        self.patient_dob_edit.setText("Next Patient DOB")    # Example
        self.provider_edit.setText("Next Provider")           # Example

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFConverterApp()
    window.show()
    sys.exit(app.exec())

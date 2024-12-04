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

# Common insurance providers (sorted alphabetically)
COMMON_INSURANCES = sorted([
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
    "WORKER'S COMP"
])

# Common CPT codes (sorted numerically)
COMMON_CPT_CODES = sorted([
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
    "99214"
])

# Common modifiers and units (sorted numerically)
COMMON_MODIFIERS = sorted([
    "1",
    "2",
    "3",
    "4",
    "25"
])

class PDFConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.extracted_data = []  # Store all extracted patient data
        self.current_patient_index = 0  # Track the current patient index

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
        self.cpt_code_edit.textChanged.connect(self.on_cpt_code_changed)  # Add text changed handler
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

        # Create a horizontal layout for the buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_entry_button)
        button_layout.addWidget(self.next_patient_button)

        extracted_data_layout.addLayout(button_layout)  # Add button layout to extracted data

        # Ensure Enter key activates the Add Entry button
        self.add_entry_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.add_entry_button.keyPressEvent = lambda event: self.add_entry_to_viewbox() if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) else None

        # Ensure Enter key activates the Add Entry button from the QLineEdit fields
        self.cpt_code_edit.returnPressed.connect(self.mod_units_edit.setFocus)  # Move to Mod/Units field
        self.mod_units_edit.returnPressed.connect(self.add_entry_to_viewbox)

        # Ensure Enter key activates the Next Patient button
        self.next_patient_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.next_patient_button.keyPressEvent = lambda event: self.next_patient() if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) else None

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
        if cpt_code and mod_units:
            self.entries_view.append(f"CPT Code: {cpt_code}, Mod/Units: {mod_units}")
            self.cpt_code_edit.clear()
            self.mod_units_edit.clear()
            self.cpt_code_edit.setFocus()  # Set focus back to the CPT Code field

    def next_patient(self):
        """Move to the next patient"""
        if self.current_patient_index < len(self.extracted_data):
            self.load_next_patient_data()
            self.insurance_edit.setFocus()  # Set focus to insurance field
        else:
            print("No more patients to process")

    def load_next_patient_data(self):
        """Load the next patient's data into the form"""
        if self.extracted_data and self.current_patient_index < len(self.extracted_data):
            patient = self.extracted_data[self.current_patient_index]
            self.patient_name_edit.setText(patient['name'])
            self.patient_dob_edit.setText(patient['dob'])
            self.provider_edit.setText(patient['provider'])
            self.insurance_edit.setText(patient.get('insurance', ''))  # Use get() with default empty string
            self.cpt_code_edit.clear()  # Clear previous CPT code entry
            self.mod_units_edit.clear()  # Clear previous Mod/Units entry
            
            # Clear the entries view box
            self.entries_view.clear()  # Clear previous entries
            
            # Increment the index for the next patient
            self.current_patient_index += 1
        else:
            print("No more patients to load.")

    def on_cpt_code_changed(self, text):
        """Handle CPT code changes"""
        if text.startswith('99'):
            self.mod_units_edit.setText('25')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFConverterApp()
    window.show()
    sys.exit(app.exec())

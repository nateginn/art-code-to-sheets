from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCompleter, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
import sys
from datetime import datetime
from pdf_to_sheets.pdf_processor import PDFProcessor
from pdf_to_sheets.sheets_manager import SheetsManager
from pdf_to_sheets.config import Config
import re

LOCATIONS = ["Greeley", "UNC", "FOCO"]
CPT_LENGTH = 5

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
        self.setWindowTitle("PDF Schedule to Sheet Converter")
        
        # Initialize data
        self.patients = []
        self.current_patient_index = 0
        self.config = Config()
        self.pdf_processor = PDFProcessor()
        self.sheets_manager = SheetsManager(self.config.config['credentials_path'])
        self.cpt_codes = []
        self.skipped_patients = set()
        
        # Setup UI
        self.init_ui()
        
    def create_completer(self, items, line_edit):
        """Create a completer with custom settings"""
        completer = QCompleter(items)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        
        def complete_text(text):
            line_edit.setText(text)
            line_edit.setCursorPosition(len(text))
        
        completer.activated.connect(complete_text)
        return completer
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(10)  # Add spacing between elements
        
        # File Selection Section
        file_group = QtWidgets.QGroupBox("PDF File Selection")
        file_layout = QVBoxLayout()
        
        file_selector = QHBoxLayout()
        self.file_label = QLabel("Selected File: None")
        self.select_button = QPushButton("Select PDF")
        self.select_button.setFixedWidth(100)
        self.select_button.clicked.connect(self.select_file)
        file_selector.addWidget(self.file_label)
        file_selector.addWidget(self.select_button)
        file_layout.addLayout(file_selector)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Patient Information Section
        patient_group = QtWidgets.QGroupBox("Patient Information")
        patient_layout = QVBoxLayout()
        
        # Current Patient Display
        self.patient_label = QLabel("Current Patient: None")
        patient_layout.addWidget(self.patient_label)
        
        # Location Input
        location_layout = QHBoxLayout()
        location_label = QLabel("Location:")
        location_label.setFixedWidth(80)
        self.location_input = QLineEdit()
        location_completer = self.create_completer(LOCATIONS, self.location_input)
        self.location_input.setCompleter(location_completer)
        location_layout.addWidget(location_label)
        location_layout.addWidget(self.location_input)
        patient_layout.addLayout(location_layout)
        
        # Insurance Input
        insurance_layout = QHBoxLayout()
        insurance_label = QLabel("Insurance:")
        insurance_label.setFixedWidth(80)
        self.insurance_input = QLineEdit()
        insurance_completer = self.create_completer(COMMON_INSURANCES, self.insurance_input)
        self.insurance_input.setCompleter(insurance_completer)
        insurance_layout.addWidget(insurance_label)
        insurance_layout.addWidget(self.insurance_input)
        patient_layout.addLayout(insurance_layout)
        
        # CPT Code Input
        cpt_layout = QHBoxLayout()
        cpt_label = QLabel("CPT Code:")
        cpt_label.setFixedWidth(80)
        self.cpt_input = QLineEdit()
        cpt_completer = self.create_completer(COMMON_CPT_CODES, self.cpt_input)
        self.cpt_input.setCompleter(cpt_completer)
        cpt_layout.addWidget(cpt_label)
        cpt_layout.addWidget(self.cpt_input)
        patient_layout.addLayout(cpt_layout)
        
        # Modifier Input
        modifier_layout = QHBoxLayout()
        modifier_label = QLabel("Modifier:")
        modifier_label.setFixedWidth(80)
        self.modifier_input = QLineEdit()
        modifier_completer = self.create_completer(COMMON_MODIFIERS, self.modifier_input)
        self.modifier_input.setCompleter(modifier_completer)
        modifier_layout.addWidget(modifier_label)
        modifier_layout.addWidget(self.modifier_input)
        patient_layout.addLayout(modifier_layout)
        
        patient_group.setLayout(patient_layout)
        layout.addWidget(patient_group)
        
        # Action Buttons Section
        button_group = QtWidgets.QGroupBox("Actions")
        button_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("Process PDF")
        self.process_btn.clicked.connect(self.process_pdf)
        self.skip_btn = QPushButton("Skip Patient")
        self.skip_btn.clicked.connect(self.skip_patient)
        
        # Initially disable buttons until file is selected
        self.process_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.skip_btn)
        button_group.setLayout(button_layout)
        layout.addWidget(button_group)
        
        # Status Bar
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Set window properties
        self.setLayout(layout)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
    def select_file(self):
        """Open file dialog to select PDF"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if file_name:
            self.file_label.setText(f"Selected File: {file_name}")
            self.pdf_path = file_name
            self.process_btn.setEnabled(True)
            self.skip_btn.setEnabled(True)
            
    def process_pdf(self):
        """Process the selected PDF file"""
        if not hasattr(self, 'pdf_path'):
            QMessageBox.warning(self, "Error", "Please select a PDF file first")
            return
            
        try:
            # Process PDF logic here
            self.patients = self.pdf_processor.extract_patients(self.pdf_path)
            if not self.patients:
                QMessageBox.warning(self, "Error", "No patient data found in PDF")
                return
                
            # Additional processing logic...
            QMessageBox.information(self, "Success", "PDF processed successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error processing PDF: {str(e)}")
            
    def skip_patient(self):
        """Skip the current patient"""
        if not self.patients:
            QMessageBox.warning(self, "Warning", "No patients to skip")
            return
            
        self.skipped_patients.add(self.current_patient_index)
        self.current_patient_index += 1
        if self.current_patient_index >= len(self.patients):
            QMessageBox.information(self, "Complete", "All patients processed")
            self.current_patient_index = 0
            
def main():
    app = QApplication(sys.argv)
    window = PDFConverterApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

# artschedretriever/loc_date_gui.py

import config
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QDateEdit, QCheckBox, QDialogButtonBox, QGroupBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime

class LocationDateDialog(QDialog):
    def __init__(self, config):
        super().__init__()
        self.selected_locations = []
        self.start_date = None
        self.end_date = None
        self.dev_folder_id = config.dev_folder_id
        self.prod_folder_id = config.prod_folder_id
        self.selected_folder_id = self.dev_folder_id  # Default to dev
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Schedule Search Parameters")
        layout = QVBoxLayout()

        # Date Selection Group
        date_group = QGroupBox("Date Selection")
        date_layout = QVBoxLayout()
        
        date_range_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit(QDate.currentDate())
        self.end_date_edit = QDateEdit(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit.setCalendarPopup(True)
        
        date_range_layout.addWidget(QLabel("Start Date:"))
        date_range_layout.addWidget(self.start_date_edit)
        date_range_layout.addWidget(QLabel("End Date:"))
        date_range_layout.addWidget(self.end_date_edit)
        date_layout.addLayout(date_range_layout)
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        # Location Selection Group
        location_group = QGroupBox("Location Selection")
        location_layout = QVBoxLayout()
        
        self.all_locations = QCheckBox("ALL Locations")
        self.greeley = QCheckBox("Greeley")
        self.unc = QCheckBox("UNC")
        self.foco = QCheckBox("FOCO")
        self.naigreeley = QCheckBox("NAI - Greeley")
        self.naifoco = QCheckBox("NAI - Fort Collins")
        
        self.all_locations.stateChanged.connect(self.toggle_locations)
        
        location_layout.addWidget(self.all_locations)
        location_layout.addWidget(self.greeley)
        location_layout.addWidget(self.unc)
        location_layout.addWidget(self.foco)
        location_layout.addWidget(self.naigreeley)
        location_layout.addWidget(self.naifoco)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        mode_group = QGroupBox("Environment Selection")
        mode_layout = QVBoxLayout()
        
        self.prod_mode = QCheckBox("Production Mode")
        self.prod_mode.stateChanged.connect(self.toggle_mode)
        
        self.mode_label = QLabel("Current Mode: Development")
        self.mode_label.setStyleSheet("color: green;")
        
        mode_layout.addWidget(self.prod_mode)
        mode_layout.addWidget(self.mode_label)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Dialog Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def toggle_locations(self, state):
        for cb in [self.greeley, self.unc, self.foco, self.naigreeley, self.naifoco]:
            cb.setEnabled(not state)
            cb.setChecked(state)

    def validate_and_accept(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        
        if start_date > end_date:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Date Range", 
                              "Start date must be before or equal to end date.")
            return

        self.start_date = start_date
        self.end_date = end_date
        
        if self.all_locations.isChecked():
            self.selected_locations = ["ART - GREELEY", "ART at UNC", "ART FOCO", "NAI - Greeley", "NAI - Fort Collins"]
        else:
            self.selected_locations = []
            if self.greeley.isChecked(): self.selected_locations.append("ART - GREELEY")
            if self.unc.isChecked(): self.selected_locations.append("ART at UNC") 
            if self.foco.isChecked(): self.selected_locations.append("ART FOCO")
            if self.naigreeley.isChecked(): self.selected_locations.append("NAI - Greeley")
            if self.naifoco.isChecked(): self.selected_locations.append("NAI - Fort Collins")
            
        if not self.selected_locations:
            QMessageBox.warning(self, "No Location Selected", 
                              "Please select at least one location.")
            return
            
        self.accept()

    def toggle_mode(self, state):
        if state:
            reply = QMessageBox.question(
                self,
                'Confirm Production Mode',
                'Are you sure you want to switch to Production mode?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.selected_folder_id = self.prod_folder_id
                self.mode_label.setText("Current Mode: Production")
                self.mode_label.setStyleSheet("color: red;")
            else:
                self.prod_mode.setChecked(False)
        else:
            self.selected_folder_id = self.dev_folder_id
            self.mode_label.setText("Current Mode: Development")
            self.mode_label.setStyleSheet("color: green;")
            
    def get_selection(self):
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "locations": self.selected_locations,
            "folder_id": self.selected_folder_id
        }

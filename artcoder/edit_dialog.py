from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCompleter
)
from PyQt6.QtCore import Qt

class EditDialog(QDialog):
    def __init__(self, parent=None, cpt_code="", mod_units="", cpt_codes=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Entry")
        self.result = None
        self.setup_ui(cpt_code, mod_units, cpt_codes)

    def setup_ui(self, cpt_code, mod_units, cpt_codes):
        layout = QVBoxLayout()
        
        # CPT Code field
        cpt_layout = QHBoxLayout()
        cpt_label = QLabel("CPT Code:")
        self.cpt_edit = QLineEdit()
        self.cpt_edit.setText(cpt_code)
        if cpt_codes:
            completer = QCompleter(cpt_codes)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.cpt_edit.setCompleter(completer)
        cpt_layout.addWidget(cpt_label)
        cpt_layout.addWidget(self.cpt_edit)
        layout.addLayout(cpt_layout)

        # Mod/Units field
        mod_layout = QHBoxLayout()
        mod_label = QLabel("Mod/Units:")
        self.mod_edit = QLineEdit()
        self.mod_edit.setText(mod_units)
        mod_layout.addWidget(mod_label)
        mod_layout.addWidget(self.mod_edit)
        layout.addLayout(mod_layout)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_values(self):
        if self.result == QDialog.DialogCode.Accepted:
            return {
                'cpt': self.cpt_edit.text().strip(),
                'mod': self.mod_edit.text().strip()
            }
        return None

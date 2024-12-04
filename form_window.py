# pdf_to_sheets/form_window.py

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from .sheets_manager import SheetsManager
from .config import Config

class EntryForm(tk.Toplevel):
   def __init__(self, parent):
       super().__init__(parent)
       self.title("Manual Entry Form")
       self.geometry("600x800")
       self.config = Config()
       self.sheets_manager = SheetsManager(self.config.get('credentials_path'))
       
       # Create main frame with scrollbar
       self.main_frame = ttk.Frame(self)
       self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
       
       # Basic fields
       self.fields = [
           ("Date", datetime.now().strftime('%m/%d/%y')),
           ("Status", ""),
           ("Patient", ""),
           ("Time", ""),
           ("Provider", ""),
           ("Type", ""),
           ("Chief Complaint", "")
       ]
       
       # Create form fields
       self.create_basic_fields()
       
       # CPT Codes section
       self.create_cpt_section()
       
       # Submit button
       self.submit_btn = ttk.Button(
           self.main_frame,
           text="Submit",
           command=self.submit_form
       )
       self.submit_btn.pack(pady=20)
       
   def create_basic_fields(self):
       for field, default in self.fields:
           frame = ttk.Frame(self.main_frame)
           frame.pack(fill=tk.X, pady=5)
           
           label = ttk.Label(frame, text=field, width=15)
           label.pack(side=tk.LEFT)
           
           entry = ttk.Entry(frame)
           entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
           entry.insert(0, default)
           setattr(self, f"{field.lower().replace(' ', '_')}_entry", entry)
   
   def create_cpt_section(self):
       # CPT Section Title
       cpt_title = ttk.Label(
           self.main_frame,
           text="CPT Codes and Units",
           font=('Helvetica', 10, 'bold')
       )
       cpt_title.pack(pady=10)
       
       # Frame for CPT entries
       self.cpt_frame = ttk.Frame(self.main_frame)
       self.cpt_frame.pack(fill=tk.X)
       
       # Button to add more CPT fields
       self.add_cpt_btn = ttk.Button(
           self.main_frame,
           text="Add CPT Code",
           command=self.add_cpt_field
       )
       self.add_cpt_btn.pack(pady=5)
       
       self.cpt_entries = []
       self.add_cpt_field()  # Add first CPT field by default
   
   def add_cpt_field(self):
       frame = ttk.Frame(self.cpt_frame)
       frame.pack(fill=tk.X, pady=2)
       
       cpt_entry = ttk.Entry(frame, width=10)
       cpt_entry.pack(side=tk.LEFT, padx=5)
       cpt_entry.insert(0, "CPT")
       
       units_entry = ttk.Entry(frame, width=5)
       units_entry.pack(side=tk.LEFT, padx=5)
       units_entry.insert(0, "Units")
       
       remove_btn = ttk.Button(
           frame,
           text="X",
           width=2,
           command=lambda f=frame: self.remove_cpt_field(f)
       )
       remove_btn.pack(side=tk.LEFT, padx=5)
       
       self.cpt_entries.append((frame, cpt_entry, units_entry))
   
   def remove_cpt_field(self, frame):
       if len(self.cpt_entries) > 1:  # Keep at least one CPT field
           for entry in self.cpt_entries:
               if entry[0] == frame:
                   self.cpt_entries.remove(entry)
                   frame.destroy()
                   break
   
   def submit_form(self):
       # Get active spreadsheet ID or create new one
       spreadsheet_id = self.config.get('active_spreadsheet_id')
       print(f"Current spreadsheet ID: {spreadsheet_id}")

       # Check if current spreadsheet exists
       if spreadsheet_id and not self.sheets_manager.check_sheet_exists(spreadsheet_id):
           print("Current spreadsheet not accessible, clearing ID...")
           self.sheets_manager.clear_invalid_sheet_id(self.config)
           spreadsheet_id = None

       # If no valid spreadsheet ID, create new sheet
       if not spreadsheet_id:
           print("Creating new spreadsheet...")
           spreadsheet_id = self.sheets_manager.create_sheet(
               self.config.get('spreadsheet_name')
           )
           if spreadsheet_id:
               self.config.set('active_spreadsheet_id', spreadsheet_id)
               print(f"New spreadsheet ID saved: {spreadsheet_id}")
           else:
               print("Failed to create new spreadsheet")
               return

       # Get values from all fields
       data = [
           self.date_entry.get(),
           self.status_entry.get(),
           self.patient_entry.get(),
           self.time_entry.get(),
           self.provider_entry.get(),
           self.type_entry.get(),
           self.chief_complaint_entry.get()
       ]
       
       # Add CPT codes and units
       for _, cpt_entry, units_entry in self.cpt_entries:
           cpt = cpt_entry.get().strip()
           units = units_entry.get().strip()
           if cpt != "CPT":  # Only check if CPT is different from placeholder
               if units and units != "Units":
                   data.append(f"{cpt} ({units})")
               else:
                   data.append(cpt)
       
       # Append data to sheet
       if spreadsheet_id:
           success = self.sheets_manager.append_row(spreadsheet_id, data)
           if success:
               print("Data added successfully!")
               print(f"Sheet URL: {self.sheets_manager.get_sheet_url(spreadsheet_id)}")
           else:
               print("Error adding data to sheet")
       
       self.destroy()

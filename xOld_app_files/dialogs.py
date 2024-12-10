# dialogs.py

import tkinter as tk
from tkinter import ttk

class EditDialog(tk.Toplevel):
    def __init__(self, parent, entry=None):
        super().__init__(parent)
        self.title("Edit CPT Code")
        self.result = None
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Create and pack widgets
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # CPT entry
        ttk.Label(frame, text="CPT Code:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cpt_var = tk.StringVar(value=entry['cpt'] if entry else '')
        self.cpt_entry = ttk.Entry(frame, textvariable=self.cpt_var)
        self.cpt_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Mod/Units entry
        ttk.Label(frame, text="Mod/Units:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.mod_var = tk.StringVar(value=entry['mod'] if entry else '')
        self.mod_entry = ttk.Entry(frame, textvariable=self.mod_var)
        self.mod_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Configure grid
        frame.columnconfigure(1, weight=1)
        
        # Set focus and bind events
        self.cpt_entry.focus_set()
        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())
        
        # Wait for window to be destroyed
        self.wait_window()
    
    def ok(self):
        self.result = {
            'cpt': self.cpt_var.get().strip(),
            'mod': self.mod_var.get().strip()
        }
        self.destroy()
    
    def cancel(self):
        self.destroy()


class ValidationDialog(tk.Toplevel):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.title("Validation Warning")
        self.result = None
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Create and pack widgets
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=message, wraplength=300).pack(pady=10)
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Change", command=self.change).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Keep As Is", command=self.keep).pack(side=tk.LEFT, padx=5)
        
        self.bind("<Escape>", lambda e: self.change())
        
        # Wait for window to be destroyed
        self.wait_window()
    
    def change(self):
        self.result = "change"
        self.destroy()
    
    def keep(self):
        self.result = "keep"
        self.destroy()

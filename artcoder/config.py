# config.py

import json
import os

class Config:
    def __init__(self):
        self.config_file = 'config.json'
        self.default_config = {
            'credentials_path': './credentials.json',
            'active_spreadsheet_id': None,
            'spreadsheet_name': 'Patient Records'
        }
        self.load_config()

    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = self.default_config
        else:
            self.config = self.default_config
            self.save_config()

    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    def get(self, key):
        """Get a configuration value"""
        return self.config.get(key, self.default_config.get(key))

    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
        self.save_config()

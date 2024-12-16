# artschedretriever/config.py

from pathlib import Path
from dotenv import load_dotenv
import os

class Config:
    def __init__(self):
        self.load_env()
        self.pdf_output_directory = os.getenv('PDF_OUTPUT_DIR', 
            str(Path.home() / 'Documents' / 'PF_Schedules'))
        self.dev_folder_id = os.getenv('DEV_FOLDER_ID')
        self.prod_folder_id = os.getenv('PROD_FOLDER_ID')
        
        if not all([self.dev_folder_id, self.prod_folder_id]):
            raise ValueError("Missing folder IDs in .env file")
    def load_env(self):
        """Load configuration from .env file"""
        env_path = Path(__file__).parent / '.env'
        load_dotenv(env_path)
        
        self.username = os.getenv('PF_USERNAME')
        self.password = os.getenv('PF_PASSWORD')
        
        if not all([self.username, self.password]):
            raise ValueError("Missing required credentials in .env file")

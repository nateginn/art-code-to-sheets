# artschedretriever/config.py

from pathlib import Path
from dotenv import load_dotenv
import os

class Config:
    def __init__(self):
        self.load_env()
        self.pdf_output_directory = os.getenv('PDF_OUTPUT_DIR', 
            str(Path.home() / 'Documents' / 'PF_Schedules'))
        
    def load_env(self):
        """Load configuration from .env file"""
        env_path = Path(__file__).parent / '.env'
        load_dotenv(env_path)
        
        self.username = os.getenv('PF_USERNAME')
        self.password = os.getenv('PF_PASSWORD')
        
        if not all([self.username, self.password]):
            raise ValueError("Missing required credentials in .env file")

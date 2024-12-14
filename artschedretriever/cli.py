# artschedretriever/cli.py

import os
import asyncio
import logging
from config import Config
from scheduler import ScheduleRetriever
from sheets_integration import SheetsManager

FOLDER_ID = '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw'
LOCATION = "UNC"
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service_account.json')

async def main():
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize components
        config = Config()
        scheduler = ScheduleRetriever(config)
        sheets_manager = SheetsManager(CREDENTIALS_PATH)

        # Run scheduler to extract data
        await scheduler.navigate_to_agenda()
        
        # Create and populate sheet
        spreadsheet_id = sheets_manager.create_and_populate_sheet(
            LOCATION,
            os.path.join(os.path.dirname(__file__), 'agenda_data.json'),
            FOLDER_ID
        )
        
        if spreadsheet_id:
            print(f"Successfully created sheet with ID: {spreadsheet_id}")
        else:
            print("Failed to create sheet")

    except Exception as e:
        logging.error(f"Process failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

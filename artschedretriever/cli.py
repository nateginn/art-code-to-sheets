# artschedretriever/cli.py

import os
import sys
import asyncio
import argparse
import logging
from config import Config
from scheduler import ScheduleRetriever
from sheets_integration import SheetsManager
from PyQt6.QtWidgets import QApplication
from gui import SheetManagementGUI

FOLDER_ID = '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw'
LOCATION = "UNC"
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service_account.json')

async def run_automation():
    """Run the automated web scraping and sheet creation process"""
    try:
        config = Config()
        scheduler = ScheduleRetriever(config)
        sheets_manager = SheetsManager(CREDENTIALS_PATH)

        await scheduler.navigate_to_agenda()
        
        spreadsheet_id = sheets_manager.create_and_populate_sheet(
            LOCATION,
            os.path.join(os.path.dirname(__file__), 'agenda_data.json'),
            FOLDER_ID
        )
        
        if spreadsheet_id:
            print(f"Successfully created sheet with ID: {spreadsheet_id}")
            return spreadsheet_id
        else:
            print("Failed to create sheet")
            return None

    except Exception as e:
        logging.error(f"Automation process failed: {str(e)}")
        raise

def run_gui():
    """Launch the GUI application"""
    app = QApplication(sys.argv)
    window = SheetManagementGUI()
    window.show()
    return app.exec()

async def main():
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description='ART Schedule Management Tool')
    parser.add_argument('--mode', choices=['auto', 'gui'], default='auto',
                       help='Run in automation mode or launch GUI (default: auto)')
    
    args = parser.parse_args()
    
    if args.mode == 'auto':
        spreadsheet_id = await run_automation()
        # Optionally launch GUI after automation
        if spreadsheet_id and input("Would you like to edit the sheet now? (y/n): ").lower() == 'y':
            run_gui()
    else:
        run_gui()

if __name__ == "__main__":
    asyncio.run(main())

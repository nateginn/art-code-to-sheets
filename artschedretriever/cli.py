# artschedretriever/cli.py

import os
import sys
import asyncio
import argparse
import logging
import json
from config import Config
from scheduler import ScheduleRetriever
from sheets_integration import SheetsManager
from PyQt6.QtWidgets import QApplication, QDialog
from gui import SheetManagementGUI
from loc_date_gui import LocationDateDialog  # Import the LocationDateDialog

FOLDER_ID = '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw'
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service_account.json')

async def run_automation():
    """Run the automated web scraping and sheet creation process"""
    try:
        # Show location/date selection dialog
        dialog = LocationDateDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            print("Operation cancelled by user")
            return None
            
        params = dialog.get_selection()  # Get selected parameters from the dialog
        config = Config()
        scheduler = ScheduleRetriever(config)
        sheets_manager = SheetsManager(CREDENTIALS_PATH)
        
        await scheduler.init_browser()  # Initialize browser once
        
        # Get data for selected date
        data = await scheduler.login(
            location=params.get('locations', ['ART at UNC'])[0],
            target_date=params.get('start_date')
        )
        
        if not data:
            print("No schedule was extracted")
            return None

        # Write data to temporary JSON file
        json_path = os.path.join(os.path.dirname(__file__), 'agenda_data.json')
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)
        
        # Get location from params for sheet creation
        location = params.get('locations', ['UNC'])[0].split(' - ')[-1]
        
        # Create sheet
        spreadsheet_id = sheets_manager.create_and_populate_sheet(
            location,
            json_path,
            FOLDER_ID
        )
        
        await scheduler.close()  # Close browser when done
        
        if spreadsheet_id:
            print(f"Successfully created sheet with ID: {spreadsheet_id}")
            return [spreadsheet_id]
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
    
    app = QApplication(sys.argv)
    spreadsheet_ids = await run_automation()
    
    if spreadsheet_ids:
        print(f"\nCreated {len(spreadsheet_ids)} sheets successfully")
        if input("Would you like to edit the sheets now? (y/n): ").lower() == 'y':
            run_gui()
    else:
        print("No sheets were created")

if __name__ == "__main__":
    asyncio.run(main())

# artschedretriever/cli.py

import os
import sys
import asyncio
import logging
import json
from datetime import datetime
from config import Config
from scheduler import ScheduleRetriever
from sheets_integration import SheetsManager
from PyQt6.QtWidgets import QApplication, QDialog
from gui import SheetManagementGUI
from loc_date_gui import LocationDateDialog

LOCATION_MAPPING = {
    "Accelerated Rehab Therapy - GREELEY": "GREELEY",
    "ART at UNC": "UNC",
    "ART FOCO": "FOCO"
}

FOLDER_ID = '1CID44P-ogKi0XPmwUppbw0Uy0YT-0Kaw'
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service_account.json')
TEMP_JSON_DIR = os.path.join(os.path.dirname(__file__), 'temp_json')
os.makedirs(TEMP_JSON_DIR, exist_ok=True)

async def create_sheets_for_location(sheets_manager, location, schedules):
    spreadsheet_ids = []
    location_name = LOCATION_MAPPING.get(location, location.split(' - ')[-1])
    print(f"\nProcessing location: {location_name}")
    
    for schedule_data in schedules:
        try:
            # Extract date from schedule data
            date_str = schedule_data['date_of_service'].split(' - ')[1]
            date_obj = datetime.strptime(date_str, '%A, %B %d, %Y')
            json_path = os.path.join(TEMP_JSON_DIR, f"agenda_data_{location_name}_{date_obj.strftime('%Y%m%d')}.json")
            
            # Create JSON file for sheet creation
            print(f"Creating JSON file for sheet: {json_path}")
            with open(json_path, "w") as f:
                json.dump(schedule_data, f, indent=4)
            
            # Create sheet
            print(f"Creating Google Sheet for {date_obj.strftime('%Y-%m-%d')}")
            spreadsheet_id = sheets_manager.create_and_populate_sheet(
                location_name,
                json_path,
                FOLDER_ID
            )
            
            # Handle sheet creation result
            if spreadsheet_id:
                print(f"Sheet created successfully with ID: {spreadsheet_id}")
                spreadsheet_ids.append(spreadsheet_id)
                
                # Clean up JSON file
                try:
                    os.remove(json_path)
                    print(f"Successfully deleted JSON file: {json_path}")
                except Exception as e:
                    print(f"Error deleting JSON file {json_path}: {str(e)}")
            else:
                print(f"Failed to create sheet for {json_path}")
                
        except Exception as e:
            print(f"Error processing schedule data: {str(e)}")
            continue
            
    return spreadsheet_ids

async def run_automation():
    try:
        dialog = LocationDateDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
            
        params = dialog.get_selection()
        config = Config()
        scheduler = ScheduleRetriever(config)
        sheets_manager = SheetsManager(CREDENTIALS_PATH)
        
        await scheduler.init_browser()
        
        all_schedules = await scheduler.process_all_locations(
            locations=params.get('locations', []),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        
        if not all_schedules:
            print("No schedules were extracted")
            return None

        all_spreadsheet_ids = []
        for location, schedules in all_schedules.items():
            location_ids = await create_sheets_for_location(sheets_manager, location, schedules)
            all_spreadsheet_ids.extend(location_ids)
        
        await scheduler.close()
        
        if all_spreadsheet_ids:
            print(f"\nSuccessfully created {len(all_spreadsheet_ids)} sheets")
            return all_spreadsheet_ids
        else:
            print("Failed to create sheets")
            return None

    except Exception as e:
        logging.error(f"Automation process failed: {str(e)}")
        raise

def run_gui():
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

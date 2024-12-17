# artschedretriever/plan.py

# artschedretriever/plan.py

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from loc_date_gui import LocationDateDialog
from config import Config
from planex import PlanExtractor
from plan_to_sheet import SheetsManager

CREDENTIALS_PATH = Path(__file__).parent.parent / 'service_account.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def format_json_filename(location, date):
    """Create standardized JSON filename from location and date"""
    try:
        # First try full day name format
        date_str = datetime.strptime(date, "%A, %B %d, %Y").strftime("%Y%m%d")
    except ValueError:
        # Fall back to abbreviated day name format
        date_str = datetime.strptime(date, "%a, %b %d, %Y").strftime("%Y%m%d")
    return f"agenda_data_{location}_{date_str}.json"

async def extract_agenda_data():
    try:
        app = QApplication([])
        config = Config()
        dialog = LocationDateDialog(config)
        
        if dialog.exec() != dialog.DialogCode.Accepted:
            logging.info("User cancelled operation")
            return

        params = dialog.get_selection()
        if not params.get('locations') or not params.get('start_date'):
            logging.error("Required parameters not selected")
            return

        extractor = PlanExtractor(config)
        await extractor.init_browser()

        try:
            all_schedules = await extractor.process_all_locations(
                params['locations'],
                params['start_date'],
                params['end_date']
            )

            sheets_manager = SheetsManager(CREDENTIALS_PATH)
            folder_id = params['folder_id']
            
            for location, schedules in all_schedules.items():
                location_short = location.split(' - ')[-1]
                
                for data in schedules:
                    json_filename = format_json_filename(location_short, data['date_of_service'])
                    output_path = Path(__file__).parent / 'temp_json' / json_filename
                    output_path.parent.mkdir(exist_ok=True)
                    
                    with open(output_path, 'w') as f:
                        json.dump(data, f, indent=4)
                    
                    spreadsheet_id = sheets_manager.create_and_populate_sheet(
                        location_short, 
                        str(output_path),
                        folder_id
                    )
                    
                    if spreadsheet_id:
                        logging.info(f"Sheet created for {location_short} with ID: {spreadsheet_id}")
                    else:
                        logging.error(f"Failed to create sheet for {location_short}")

        finally:
            await extractor.close()

    except Exception as e:
        logging.error(f"Error during extraction: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(extract_agenda_data())
    print("Plan extraction and processing completed.")

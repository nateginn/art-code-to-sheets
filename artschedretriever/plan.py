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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def format_json_filename(location, date):
    """Create standardized JSON filename from location and date"""
    date_str = datetime.strptime(date, "%a, %b %d, %Y").strftime("%Y%m%d")
    return f"agenda_data_{location}_{date_str}.json"

async def extract_agenda_data():
    try:
        # Initialize Qt Application
        app = QApplication([])
        
        # Open Location and Date GUI
        config = Config()
        dialog = LocationDateDialog(config)
        if dialog.exec() != dialog.DialogCode.Accepted:
            logging.info("User cancelled operation")
            return

        # Get selected params and log them
        params = dialog.get_selection()
        logging.info(f"Selected date: {params.get('start_date')}")
        logging.info(f"Selected locations: {params.get('locations')}")
        
        if not params.get('locations') or not params.get('start_date'):
            logging.error("Required parameters not selected")
            return

        # Initialize config and extractor
        config = Config()
        extractor = PlanExtractor(config)


        # Launch browser
        await extractor.init_browser()

        try:
            # Login
            if not await extractor.login():
                logging.error("Login failed")
                return

            # Process each selected location
            for location in params['locations']:
                logging.info(f"Processing location: {location}")
                
                # Navigate to agenda URL
                agenda_url = extractor.get_agenda_url(location)
                await extractor.page.goto(agenda_url)
                await asyncio.sleep(1)  # Wait for page load
                
                # Click date picker and wait
                await extractor.page.click("#date-picker-button")
                await asyncio.sleep(1)
                
                # Format target date for picker
                target_date = params['start_date']
                logging.info(f"Setting date to: {target_date}")
                
                # Set month/year
                target_month = target_date.strftime("%B %Y")
                current_month = await extractor.page.locator(".datepicker-days table thead tr th.switch").text_content()

                while current_month != target_month:
                    logging.info(f"Current month: {current_month}, Target: {target_month}")
                    await extractor.page.click(".datepicker-days th.prev")
                    await asyncio.sleep(3)
                    current_month = await extractor.page.locator(".datepicker-days table thead tr th.switch").text_content()

                # Select day
                target_day = str(target_date.day)
                await extractor.page.click(f"td.day:not(.old):not(.new):text('{target_day}')")
                await asyncio.sleep(1)

                # Switch location if needed
                location_short = location.split(' - ')[-1]
                await extractor.page.click(".scheduler-toolbar__select-facilities .composable-select__choice")
                await asyncio.sleep(1)
                await extractor.page.click(f"li.composable-select__result-item a:text('{location}')")
                await asyncio.sleep(1)
                
                # Extract data
                data = await extractor.extract_agenda_data()
                if not data:
                    logging.error(f"No data extracted for {location}")
                    continue

                # Save to JSON and create sheet
                json_filename = format_json_filename(location_short, data['date_of_service'])
                output_path = Path(__file__).parent / 'temp_json' / json_filename
                output_path.parent.mkdir(exist_ok=True)
                
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                sheets_manager = SheetsManager(CREDENTIALS_PATH)
                spreadsheet_id = sheets_manager.create_and_populate_sheet(
                    location_short, 
                    str(output_path),
                    params.get('folder_id')
                )
                
                if spreadsheet_id:
                    logging.info(f"Data saved and sheet created with ID: {spreadsheet_id}")
                else:
                    logging.error("Failed to create Google Sheet")
                    logging.info(f"Data saved to {output_path}")

        finally:
            await extractor.close()

    except Exception as e:
        logging.error(f"Error during extraction: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(extract_agenda_data())

    print("Plan extraction and processing completed.")

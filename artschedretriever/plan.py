# artschedretriever/plan.py

import asyncio
import logging
from planex import PlanExtractor
from loc_date_gui import LocDateGUI
from config import Config

def format_json_filename(location, date):
    return f"{location}.{date}.json"

async def extract_and_process_data():
    try:
        # Open Location and Date GUI
        gui = LocDateGUI()
        location, date = gui.get_location_and_date()

        if not location or not date:
            print("Location or date not selected.")
            return

        # Initialize configuration and PlanExtractor
        config = Config()
        plan_extractor = PlanExtractor(config)

        # Launch the browser
        await plan_extractor.init_browser()

        # Log in to the system and handle 2FA
        logged_in = await plan_extractor.login()
        if not logged_in:
            print("Login failed.")
            return

        # Navigate to agenda URL
        agenda_url = plan_extractor.get_agenda_url(location, date)
        await plan_extractor.goto(agenda_url)

        # Extract patient data from the agenda page
        patient_data = await plan_extractor.extract_agenda_data()

        # Format and save patient data to JSON
        json_filename = format_json_filename(location, date)
        plan_extractor.save_json(patient_data, json_filename)
        print(f"Patient data saved to {json_filename}")

        # Process each patient: navigate to their encounter and extract plan
        for patient in patient_data:
            encounter_url = patient.get("view_encounter_url")
            if not encounter_url:
                continue

            # Navigate to the encounter page
            await plan_extractor.goto(encounter_url)

            # Extract plan data
            plan_data = await plan_extractor.extract_plan_data()
            patient["plan"] = plan_data

            # Run coder script on the extracted plan data
            cpt_codes = plan_extractor.run_coder(plan_data)
            patient["cpt_codes"] = cpt_codes

        # Save updated patient data with plan and CPT codes
        plan_extractor.save_json(patient_data, json_filename)
        print(f"Updated patient data saved to {json_filename}")

    except Exception as e:
        logging.error(f"Error during plan extraction and processing: {str(e)}")
    finally:
        await plan_extractor.close()

if __name__ == "__main__":
    asyncio.run(extract_and_process_data())

    print("Plan extraction and processing completed.")

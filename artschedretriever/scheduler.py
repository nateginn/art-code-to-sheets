# artschedretriever/scheduler.py
# No changes needed in scheduler.py for folder ID integration
import asyncio
import logging
import json
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

class ScheduleRetriever:
    def __init__(self, config):
        self.config = config
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.agenda_url = "https://static.practicefusion.com/apps/ehr/index.html#/PF/schedule/scheduler/agenda"

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def login(self, location=None, target_date=None):
        try:
            await self.page.goto("https://static.practicefusion.com")
            await self.page.wait_for_selector("input[type='email']", timeout=60000)  # Wait for the email input to be visible
            await self.page.fill("input[type='email']", self.config.username)
            await self.page.fill("input[type='password']", self.config.password)
            await self.page.click("button[type='submit']")
            
            print("Waiting for user to complete 2FA...")
            await asyncio.sleep(20)
            
            print("Navigating to agenda...")
            await self.page.goto(self.agenda_url)
            print("at agenda...")
            await asyncio.sleep(1)

            print("Opening location dropdown...")
            await self.page.click(".scheduler-toolbar__select-facilities .composable-select__choice")
            await asyncio.sleep(1)
            
            location_text = location if location else "ART at UNC"
            print(f"Selecting {location_text}...")
            await self.page.click(f"li.composable-select__result-item a:text('{location_text}')")
            
            print(f"Location selection attempted for {location_text}, pausing...")
            await asyncio.sleep(1)
            
            # Select Date
            print("Opening datepicker...")
            await self.page.click("#date-picker-button")
            await asyncio.sleep(1)

            if target_date:
                target_month = target_date.strftime("%B %Y")
                target_day = str(target_date.day)
            else:
                target_month = "August 2024"
                target_day = "8"

            current_month = await self.page.locator(".datepicker-days table thead tr th.switch").text_content()

            while current_month != target_month:
                await self.page.click(".datepicker-days th.prev")
                await asyncio.sleep(1)
                current_month = await self.page.locator(".datepicker-days table thead tr th.switch").text_content()
            
            print(f"{target_month} selected.")
            await asyncio.sleep(1)

            print(f"Selecting date in {target_month}...")
            await self.page.click(f"td.day:not(.old):not(.new):text('{target_day}')")
            await asyncio.sleep(2)
            
            # Print Schedule with Playwright
            print("Starting the process to print the schedule...")

            try:
                # Step 1: Trigger the 'Print Schedule' button
                print("Attempting to click the 'Print Schedule' button...")
                await self.page.click("button.btn--default[data-element='btn-schedule-print']")
                print("'Print Schedule' button clicked successfully. Waiting for the page to load printable format...")
                await asyncio.sleep(3)  # Allow time for the printable format to load

                # Step 2: Locate the printable agenda content
                print("Locating the printable agenda content...")
                try:
                    # Drill down step by step
                    print("Finding iframe containing agenda items...")
                    iframe_element = await self.page.wait_for_selector("iframe#print-modal-frame", timeout=10000)
                    iframe = await iframe_element.content_frame()
                    if not iframe:
                        raise Exception("Failed to access the iframe.")
                    await asyncio.sleep(2)

                    print("Locating the agenda container...")
                    agenda_container = await iframe.wait_for_selector("div.print-agenda-items.print-only", timeout=10000)
                    await asyncio.sleep(2)

                    # Extract the date of service
                    date_element = await agenda_container.query_selector("div.inline-flex-group-v2 h3")
                    date_of_service = await date_element.text_content() if date_element else "Date not found"
                    print(f"Extracted date of service: {date_of_service}")

                    # Check if date_of_service is valid
                    if date_of_service == "Date not found":
                        raise Exception("Failed to extract date of service")

                    print("Finding patient rows...")
                    patient_rows = await agenda_container.query_selector_all("tr.content-container")
                    print(f"Found {len(patient_rows)} patient rows.")

                    patients = []
                    for index, row in enumerate(patient_rows):
                        print(f"Processing row {index + 1}...")
                        await asyncio.sleep(1)

                        patient_name_element = await row.query_selector("td.patient-column")
                        patient_name = await patient_name_element.inner_text() if patient_name_element else "Name not found"

                        patient_birthday_element = await row.query_selector("div.birthday")
                        patient_birthday = await patient_birthday_element.text_content() if patient_birthday_element else "Birthday not found"

                        provider_element = await row.query_selector("td.provider-column")
                        provider_name = await provider_element.text_content() if provider_element else "Provider not found"

                        patient_data = {
                            "name": patient_name.strip(),
                            "birthday": patient_birthday.strip(),
                            "provider": provider_name.strip()
                        }
                        print(f"Extracted data: {patient_data}")
                        patients.append(patient_data)

                    print("Saving data to 'agenda_data.json'...")
                    schedule_data = {"date_of_service": date_of_service, "patients": patients}
                    with open("agenda_data.json", "w") as file:
                        json.dump(schedule_data, file, indent=4)
                    print("Data saved successfully to JSON.")
                    await asyncio.sleep(2)

                    # Move return data after closing print preview
                    schedule_return = {"date_of_service": date_of_service, "patients": patients}

                    print("Closing print preview...")
                    try:
                        await self.page.click("a.close-link")
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"Warning: Could not close print preview: {e}")

                    return schedule_return


                except Exception as e:
                    print(f"Error during content extraction: {e}")
                    return None

            except Exception as e:
                print(f"Failed to trigger or load the printable agenda format: {e}")
                return None

        except Exception as e:
            logging.error(f"Navigation failed: {str(e)}")
            raise

    async def close(self):
        if self.playwright:
            await self.playwright.stop()

    async def get_date_range(self, start_date, end_date):
        """Generate list of dates between start and end dates inclusive"""
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list


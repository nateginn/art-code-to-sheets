# artschedretriever/scheduler.py
import asyncio
import logging
import json
from playwright.async_api import async_playwright

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

    async def login(self):
        try:
            await self.page.goto("https://static.practicefusion.com")
            # await self.page.wait_for_load_state("networkidle")
            
            await self.page.fill("input[type='email']", self.config.username)
            await self.page.fill("input[type='password']", self.config.password)
            await self.page.click("button[type='submit']")
            
            print("Waiting for user to complete 2FA...")
            await asyncio.sleep(15)
            
            print("Navigating to agenda...")
            await self.page.goto(self.agenda_url)
            print("at agenda...")
            await asyncio.sleep(1)

            # Select location
            print("Opening location dropdown...")
            await self.page.click(".scheduler-toolbar__select-facilities .composable-select__choice")
            await asyncio.sleep(1)
            
            print("Selecting ART at UNC...")
            await self.page.click("li.composable-select__result-item a:text('ART at UNC')")
            
            print("Location selection attempted, pausing...")
            await asyncio.sleep(1)
            
           # Select Date
            print("Opening datepicker...")
            await self.page.click("#date-picker-button")
            await asyncio.sleep(1)

            # Navigate to desired month (if needed)
            current_month = await self.page.locator(".datepicker-days table thead tr th.switch").text_content()
            target_month = "November 2024"  # You may want to make this configurable

            while current_month != target_month:
                await self.page.click(".datepicker-days th.prev")
                await asyncio.sleep(2)
                current_month = await self.page.locator(".datepicker-days table thead tr th.switch").text_content()  # Updated  
            print(f"{target_month} selected.")
            await asyncio.sleep(3)

            print(f"Selecting date in {target_month}...")
            await self.page.click("td.day:not(.old):not(.new):text('21')")  # Excludes days from prev/next months
            await asyncio.sleep(5)
            
             # Print Schedule with Playwright
            print("Starting the process to print the schedule...")

            try:
                # Step 1: Trigger the 'Print Schedule' button
                print("Attempting to click the 'Print Schedule' button...")
                await self.page.click("button.btn--default[data-element='btn-schedule-print']")
                print("'Print Schedule' button clicked successfully. Waiting for the page to load printable format...")
                await asyncio.sleep(5)  # Allow time for the printable format to load

                # Step 2: Locate the printable agenda content
                print("Locating the printable agenda content...")
                try:
                    # Drill down step by step
                    print("Finding iframe containing agenda items...")
                    iframe_element = await self.page.wait_for_selector("iframe#print-modal-frame", timeout=10000)
                    iframe = await iframe_element.content_frame()
                    if not iframe:
                        raise Exception("Failed to access the iframe.")
                    await asyncio.sleep(3)

                    print("Locating the agenda container...")
                    agenda_container = await iframe.wait_for_selector("div.print-agenda-items.print-only", timeout=10000)
                    await asyncio.sleep(3)

                    print("Extracting the date of service...")
                    date_element = await agenda_container.query_selector("div.inline-flex-group-v2 h3")
                    date_of_service = await date_element.text_content() if date_element else "Date not found"
                    print(f"Date of Service: {date_of_service}")

                    print("Finding patient rows...")
                    patient_rows = await agenda_container.query_selector_all("tr.content-container")
                    print(f"Found {len(patient_rows)} patient rows.")

                    patients = []
                    for index, row in enumerate(patient_rows):
                        print(f"Processing row {index + 1}...")
                        await asyncio.sleep(3)

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
                    with open("agenda_data.json", "w") as file:
                        json.dump({"date_of_service": date_of_service, "patients": patients}, file, indent=4)
                    print("Data saved successfully.")

                except Exception as e:
                    print(f"Error during content extraction: {e}")

            except Exception as e:
                print(f"Failed to trigger or load the printable agenda format: {e}")

        except Exception as e:
            logging.error(f"Navigation failed: {str(e)}")
            raise

    async def close(self):
        if self.playwright:
            await self.playwright.stop()

    async def navigate_to_agenda(self):
        try:
            await self.init_browser()
            await self.login()
            await self.close()
        except Exception as e:
            logging.error(f"Error in navigation: {str(e)}")
            raise

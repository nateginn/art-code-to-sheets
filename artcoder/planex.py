import os
import json
import logging
import asyncio
import re
from playwright.async_api import async_playwright
from coder import PlanProcessor
from datetime import datetime, timedelta

class PlanExtractor:
    def __init__(self, config):
        self.config = config
        self.browser = None
        self.page = None
        self.playwright = None
        self.processed_dates = {}
        self.current_location = None

    async def init_browser(self):
        """Initialize browser instance"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.page = await self.browser.new_page()
    
    async def login(self):
        """Handle login and 2FA process"""
        try:
            await self.page.goto("https://static.practicefusion.com")
            await self.page.wait_for_selector("input[type='email']", timeout=60000)
            await self.page.fill("input[type='email']", self.config.username)
            await self.page.fill("input[type='password']", self.config.password)
            await self.page.click("button[type='submit']")
            
            await asyncio.sleep(20)  # 2FA wait
            
            return True
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False
        
    def get_agenda_url(self):
        """Generate agenda URL"""
        return "https://static.practicefusion.com/apps/ehr/index.html#/PF/schedule/scheduler/agenda"

    async def switch_location(self, location):
        if location != self.current_location:
            try:
                await self.page.click(".scheduler-toolbar__select-facilities .composable-select__choice")
                await asyncio.sleep(1)
                await self.page.click(f"li.composable-select__result-item a:text('{location}')")
                await asyncio.sleep(1)
                self.current_location = location
                return True
            except Exception as e:
                logging.error(f"Location switch error: {str(e)}")
                return False
        return True
            
    async def select_date(self, target_date):
        try:
            await self.page.click("#date-picker-button")
            await asyncio.sleep(1)

            target_month = target_date.strftime("%B %Y")
            target_day = str(target_date.day)
            current_month = await self.page.locator(".datepicker-days table thead tr th.switch").text_content()

            while current_month != target_month:
                await self.page.click(".datepicker-days th.prev")
                await asyncio.sleep(1)
                current_month = await self.page.locator(".datepicker-days table thead tr th.switch").text_content()

            await self.page.click(f"td.day:not(.old):not(.new):text('{target_day}')")
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Date selection error: {str(e)}")
            raise

    async def process_all_locations(self, locations, start_date, end_date):
        if not await self.login():
            raise Exception("Initial login failed")

        await self.page.goto(self.get_agenda_url())
        await asyncio.sleep(1)

        all_schedules = {}
        for location in locations:
            print(f"Processing location: {location}")
            schedules = await self.process_location_dates(location, start_date, end_date)
            if schedules:
                all_schedules[location] = schedules
            await asyncio.sleep(2)  # Delay between locations
        
        return all_schedules
    
    async def process_location_dates(self, location, start_date, end_date):
        if not await self.switch_location(location):
            return None

        if location not in self.processed_dates:
            self.processed_dates[location] = set()

        schedules = []
        current_date = start_date
        
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            if date_key not in self.processed_dates[location]:
                await self.select_date(current_date)
                schedule_data = await self.extract_agenda_data()
                
                if schedule_data and schedule_data.get("patients"):
                    schedules.append(schedule_data)
                    self.processed_dates[location].add(date_key)
            
            current_date += timedelta(days=1)
        
        return schedules
    
    async def extract_agenda_data(self):
        """Extract all patient data from agenda page and process encounters"""
        try:
            # Get date of service
            date_element = await self.page.wait_for_selector(".readable-date-container .header4semibold")
            date_of_service = await date_element.text_content()

            # Get patient rows
            patient_rows = await self.page.query_selector_all(".slc-row.appointment-container")
            patients = []
            
            # Initialize plan processor
            processor = PlanProcessor()

            for i, row in enumerate(patient_rows):
                # Extract basic patient info
                name = await row.query_selector(".patient-column .lead a")
                birthday = await row.query_selector(".birthday .text-color-default")
                provider = await row.query_selector(".provider-column .text-color-default")
                status = await row.query_selector(".status-column .display-name")
                encounter_link = await row.query_selector(".view-encounter a")

                # Build patient data dictionary
                patient_data = {
                    "name": await name.text_content() if name else "",
                    "birthday": await birthday.text_content() if birthday else "",
                    "provider": await provider.text_content() if provider else "",
                    "encounter_url": await encounter_link.get_attribute("href") if encounter_link else "",
                    "status": await status.text_content() if status else ""
                }

                # Clean whitespace
                patient_data = {k: v.strip() for k, v in patient_data.items()}

                # Extract encounter data
                if patient_data["encounter_url"]:
                    is_last_patient = (i == len(patient_rows) - 1)
                    encounter_data = await self.extract_encounter_data(patient_data["encounter_url"], is_last_patient)
                    if encounter_data:
                        # Process plan and get codes
                        plan_result = processor.process_plan(
                            encounter_data["insurance"],
                            encounter_data["plan_text"]
                        )
                        
                        # Add to patient data
                        patient_data.update({
                            "insurance": encounter_data["insurance"],
                            "plan": plan_result["procedures"],
                            "codes": plan_result["codes"]
                        })

                patients.append(patient_data)

            return {
                "date_of_service": date_of_service.strip(),
                "patients": patients
            }

        except Exception as e:
            logging.error(f"Data extraction error: {str(e)}")
            return None
        
    async def extract_encounter_data(self, encounter_url, is_last_patient=False):
        """Extract insurance from pin note and plan text from encounter page"""
        try:
            # Navigate to full URL
            full_url = f"https://static.practicefusion.com/apps/ehr/index.html{encounter_url}"
            print(f"\nNavigating to: {encounter_url}")
            await self.page.goto(full_url)
            await asyncio.sleep(2)

            # Get insurance from pin note - find first non-empty line
            pin_note = await self.page.query_selector("[data-element='patient-pinned-note-text'] .pf-rich-text")
            insurance_line = ""

            if pin_note:
                # First try paragraphs
                paragraphs = await pin_note.query_selector_all("p")
                
                for p in paragraphs:
                    text_content = (await p.inner_text()).strip()
                    if text_content and not text_content.isspace():
                        insurance_line = text_content.split('\n')[0].strip()
                        break
                
                # If no paragraph text found, try direct text content
                if not insurance_line:
                    direct_text = (await pin_note.text_content()).strip()
                    if direct_text and not direct_text.isspace():
                        insurance_line = direct_text.split('\n')[0].strip()

            print(f"Found insurance: {insurance_line}")

            # Extract the first word for billing
            insurance_first_word = insurance_line.split()[0] if insurance_line else "UNKNOWN"

            # Get plan text - Handle both signed and unsigned notes
            plan_text = ""
            plan_element = None
            try:
                # Try unsigned note selector first
                unsigned_selector = "[data-element='plan-note'] .editor[data-element='rich-text-editor']"
                plan_element = await self.page.query_selector(unsigned_selector)
                
                if not plan_element:
                    # Try signed note selector if unsigned not found
                    signed_selector = "[data-element='plan-note-read-only'] .pf-rich-text"
                    plan_element = await self.page.query_selector(signed_selector)

                if plan_element:
                    plan_text = await plan_element.inner_html()
                else:
                    logging.warning(f"Could not find plan text element for URL: {encounter_url}")
                    
            except Exception as e:
                logging.error(f"Error finding plan element: {e} for URL: {encounter_url}")
            
            print(f"\nRaw plan text found: {plan_text[:100]}...")  # Show first 100 chars

            # Clean plan text
            print("\nCleaning plan text...")
            plan_text = re.sub(r'<br\s*/?>', '\n', plan_text)
            plan_text = re.sub(r'<[^>]+>', '', plan_text)
            plan_text = re.sub(r'\n\s*\n', '\n', plan_text).strip()
            print(f"Cleaned plan text: {plan_text}")

            result = {
                "insurance": insurance_line,
                "insurance_bill": insurance_first_word.upper(),
                "plan_text": plan_text
            }

            if is_last_patient:
                await self.page.goto(self.get_agenda_url())
                await asyncio.sleep(1)

            print("\nReturning data:", result)
            return result

        except Exception as e:
            logging.error(f"Error extracting encounter data: {str(e)}")
            print(f"Error in extraction: {str(e)}")
            return None

    async def close(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

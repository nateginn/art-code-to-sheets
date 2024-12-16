import os
import json
import logging
import asyncio
import re
from playwright.async_api import async_playwright
from coder import PlanProcessor

class PlanExtractor:
    def __init__(self, config):
        self.config = config
        self.browser = None
        self.page = None
        self.playwright = None

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

    def get_agenda_url(self, location):
        """Generate agenda URL"""
        return "https://static.practicefusion.com/apps/ehr/index.html#/PF/schedule/scheduler/agenda"

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

            for row in patient_rows:
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
                    encounter_data = await self.extract_encounter_data(patient_data["encounter_url"])
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
        
    async def extract_encounter_data(self, encounter_url):
        """Extract insurance from pin note and plan text from encounter page"""
        try:
            # Navigate to full URL
            full_url = f"https://static.practicefusion.com/apps/ehr/index.html{encounter_url}"
            print(f"\nNavigating to: {encounter_url}")
            await self.page.goto(full_url)
            await asyncio.sleep(2)

            # Get insurance from pin note
            pin_note = await self.page.wait_for_selector("[data-element='patient-pinned-note-text'] .pf-rich-text p")
            insurance_line = await pin_note.text_content() if pin_note else ""
            print(f"Found insurance: {insurance_line}")

            # Extract the first word of the insurance line
            insurance_first_word = insurance_line.split()[0] if insurance_line else "UNKNOWN"

            # Wait for and get plan text
            plan_element = await self.page.wait_for_selector("[data-element='plan-note'] .editor[data-element='rich-text-editor']")
            plan_text = await plan_element.inner_html() if plan_element else ""
            print(f"\nRaw plan text found: {plan_text[:100]}...")  # Show first 100 chars

            # Clean plan text
            print("\nCleaning plan text...")
            plan_text = re.sub(r'<br\s*/?>', '\n', plan_text)
            plan_text = re.sub(r'<[^>]+>', '', plan_text)
            plan_text = re.sub(r'\n\s*\n', '\n', plan_text).strip()
            print(f"Cleaned plan text: {plan_text}")

            result = {
                "insurance": insurance_line.strip(),            # Full line for spreadsheet
                "insurance_bill": insurance_first_word.upper(),  # First word for coding
                "plan_text": plan_text
            }
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

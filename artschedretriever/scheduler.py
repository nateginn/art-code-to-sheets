# artschedretriever/scheduler.py

import asyncio
import logging
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
        self.processed_dates = {}
        self.current_location = None

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

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

    async def extract_schedule_data(self):
        try:
            await self.page.click("button.btn--default[data-element='btn-schedule-print']")
            await asyncio.sleep(2)

            iframe = await (await self.page.wait_for_selector("iframe#print-modal-frame")).content_frame()
            container = await iframe.wait_for_selector("div.print-agenda-items.print-only")
            
            date_element = await container.query_selector("div.inline-flex-group-v2 h3")
            date_of_service = await date_element.text_content() if date_element else None
            
            if not date_of_service:
                return None

            patient_rows = await container.query_selector_all("tr.content-container")
            patients = []
            
            for row in patient_rows:
                patient_name = await (await row.query_selector("td.patient-column")).inner_text()
                birthday = await (await row.query_selector("div.birthday")).text_content()
                provider = await (await row.query_selector("td.provider-column")).text_content()
                
                patients.append({
                    "name": patient_name.strip(),
                    "birthday": birthday.strip(),
                    "provider": provider.strip()
                })

            await self.page.click("a.close-link")
            await asyncio.sleep(1)
            
            return {"date_of_service": date_of_service, "patients": patients}
            
        except Exception as e:
            logging.error(f"Data extraction error: {str(e)}")
            return None

    async def login(self):
        try:
            await self.page.goto("https://static.practicefusion.com")
            await self.page.wait_for_selector("input[type='email']", timeout=60000)
            await self.page.fill("input[type='email']", self.config.username)
            await self.page.fill("input[type='password']", self.config.password)
            await self.page.click("button[type='submit']")
            
            await asyncio.sleep(20)  # 2FA wait
            
            await self.page.goto(self.agenda_url)
            await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False

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
                schedule_data = await self.extract_schedule_data()
                
                if schedule_data and schedule_data.get("patients"):
                    schedules.append(schedule_data)
                    self.processed_dates[location].add(date_key)
            
            current_date += timedelta(days=1)
        
        return schedules

    async def process_all_locations(self, locations, start_date, end_date):
        if not await self.login():
            raise Exception("Initial login failed")

        all_schedules = {}
        for location in locations:
            print(f"Processing location: {location}")
            schedules = await self.process_location_dates(location, start_date, end_date)
            if schedules:
                all_schedules[location] = schedules
            await asyncio.sleep(2)  # Delay between locations
        
        return all_schedules

    async def close(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

import os
import json
import asyncio
from playwright.async_api import async_playwright

class PlanExtractor:
    def __init__(self, config):
        self.config = config
        self.browser = None
        self.page = None

    async def init_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.page = await self.browser.new_page()

    async def login(self):
        await self.page.goto(self.config['login_url'])
        await self.page.fill('#username', self.config['username'])
        await self.page.fill('#password', self.config['password'])
        await self.page.click('#login-button')

        # Wait for 2FA input if needed
        await self.page.wait_for_selector('#2fa-input', timeout=10000)
        print("Enter your 2FA code:")
        two_fa_code = input()
        await self.page.fill('#2fa-input', two_fa_code)
        await self.page.click('#2fa-submit')

        # Wait for successful navigation
        return await self.page.wait_for_selector('#agenda', timeout=15000)

    async def goto(self, url):
        await self.page.goto(url)

    def get_agenda_url(self, location, date):
        return f"{self.config['base_url']}/schedule/{location}/{date}/agenda"

    async def extract_agenda_data(self):
        await self.page.wait_for_selector('#agenda-items')
        patients = []

        agenda_items = await self.page.query_selector_all('.slc-row.appointment-container')
        for item in agenda_items:
            name = await item.query_selector_eval('.patient-column .lead a', 'el => el.textContent.trim()')
            dob = await item.query_selector_eval('.birthday .text-color-default', 'el => el.textContent.trim()')
            provider = await item.query_selector_eval('.provider-column .text-color-default', 'el => el.textContent.trim()')
            status = await item.query_selector_eval('.status-column .display-name', 'el => el.textContent.trim()')
            encounter_url = await item.query_selector_eval('.view-encounter a', 'el => el.getAttribute("href")')

            patients.append({
                "name": name,
                "dob": dob,
                "provider": provider,
                "status": status,
                "view_encounter_url": encounter_url
            })

        return patients

    async def extract_plan_data(self):
        await self.page.wait_for_selector('[data-element="plan-note"] .editor')
        plan_content = await self.page.query_selector_eval(
            '[data-element="plan-note"] .editor', 'el => el.innerHTML.trim()')
        return plan_content

    def run_coder(self, plan_data):
        # Mocking coder logic
        # Replace this with actual script call if needed
        return {
            "cpt_codes": ["99203", "97140"],
            "units": [1, 2]
        }

    def save_json(self, data, filename):
        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)

    async def close(self):
        if self.browser:
            await self.browser.close()

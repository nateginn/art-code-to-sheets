# artschedretriever/scheduler.py

from playwright.async_api import async_playwright
import logging
from datetime import datetime
import os
from pathlib import Path
import asyncio
import sys
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QLabel, 
                            QApplication)
from PyQt6.QtCore import Qt, QTimer

class FlowControl(QWidget):
    def __init__(self):
        super().__init__()
        self.future = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Schedule Retrieval Flow')
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Waiting to start...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.continue_button = QPushButton('Continue')
        self.continue_button.clicked.connect(self.on_continue)
        layout.addWidget(self.continue_button)
        
        self.setLayout(layout)
        self.setFixedSize(400, 200)
        
        # Keep UI responsive
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(100)
        
    def on_continue(self):
        if self.future and not self.future.done():
            self.future.set_result(True)
            
    def update_status(self, message):
        self.status_label.setText(message)
        
    def wait_for_continue(self):
        self.future = asyncio.Future()
        return self.future

class ScheduleRetriever:
    def __init__(self, config):
        self.config = config
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.locations = ["Greeley", "UNC", "FOCO"]
        self.base_url = "https://static.practicefusion.com/apps/ehr/index.html#/PF/schedule/scheduler/agenda"
        self.landing_url = "https://static.practicefusion.com/apps/ehr/index.html#/PF/home/main"
        self.output_dir = Path(self.config.pdf_output_directory)
        self.flow_control = FlowControl()
        self.flow_control.show()
        
    async def wait_for_continue(self, message):
        self.flow_control.update_status(message)
        await self.flow_control.wait_for_continue()
        
    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
    async def login(self):
        try:
            await self.page.goto("https://static.practicefusion.com")
            await self.page.wait_for_load_state("networkidle")
            
            # Fill credentials
            await self.page.fill("input[type='email']", self.config.username)
            await self.page.fill("input[type='password']", self.config.password)
            
            await self.wait_for_continue("Click Continue to submit login")
            await self.page.click("button[type='submit']")
            
            await self.wait_for_continue("Complete 2FA verification and click Continue")
            
            # Wait for landing page
            await self.page.wait_for_url(self.landing_url, timeout=60000)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            await self.wait_for_continue("Landing page loaded. Click Continue to proceed")
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            raise
            
    async def navigate_to_schedule(self, date_str):
        try:
            await self.wait_for_continue("Click Continue to navigate to schedule")
            
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            await self.wait_for_continue("Schedule page loaded. Click Continue to proceed")
            
            print(f"Will set date to: {date_str}")
            
        except Exception as e:
            logging.error(f"Navigation failed: {str(e)}")
            raise
            
    async def check_schedule_exists(self, location):
        try:
            # Logic to check if schedule has appointments
            location_selector = await self.page.wait_for_selector(f"text={location}")
            await location_selector.click()
            
            # Check for appointments (adjust selector based on actual page structure)
            appointments = await self.page.query_selector_all(".appointment-slot")
            return len(appointments) > 0
            
        except Exception as e:
            logging.error(f"Schedule check failed for {location}: {str(e)}")
            return False
            
    async def save_schedule_pdf(self, date_str, location):
        try:
            filename = f"schedule_{date_str}_{location}.pdf"
            filepath = self.output_dir / filename
            
            # Ensure directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Print to PDF
            await self.page.pdf(path=str(filepath))
            return filepath
            
        except Exception as e:
            logging.error(f"PDF save failed: {str(e)}")
            raise
            
    async def close(self):
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            if self.flow_control:
                self.flow_control.close()
        except Exception as e:
            logging.error(f"Error during close: {str(e)}")
            
    async def retrieve_schedules(self, date_str):
        try:
            await self.init_browser()
            await self.login()
            
            results = []
            for location in self.locations:
                await self.navigate_to_schedule(date_str)
                if await self.check_schedule_exists(location):
                    pdf_path = await self.save_schedule_pdf(date_str, location)
                    results.append({
                        'location': location,
                        'date': date_str,
                        'pdf_path': pdf_path
                    })
                    
            return results
            
        except Exception as e:
            logging.error(f"Error retrieving schedules: {str(e)}")
            raise
        finally:
            await self.close()
            

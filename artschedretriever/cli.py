# artschedretriever/cli.py

import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from config import Config
from scheduler import ScheduleRetriever
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import sys

def parse_args():
    parser = argparse.ArgumentParser(description='Retrieve Practice Fusion Schedules')
    parser.add_argument('--date', help='Date to retrieve (YYYY-MM-DD)')
    return parser.parse_args()

async def main(app):
    args = parse_args()
    
    # Load config
    config = Config()
    
    # Use provided date or default to tomorrow
    target_date = args.date if args.date else (
        datetime.now() + timedelta(days=1)
    ).strftime('%Y-%m-%d')
    
    # Initialize and run scheduler
    scheduler = ScheduleRetriever(config)
    try:
        results = await scheduler.retrieve_schedules(target_date)
        
        # Print results
        for result in results:
            print(f"Retrieved schedule for {result['location']} on {result['date']}")
            print(f"PDF saved to: {result['pdf_path']}")
            
    except Exception as e:
        print(f"Error retrieving schedules: {e}")
        
    finally:
        app.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set up event loop
    loop = asyncio.get_event_loop()
    
    # Create timer to process Qt events
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)
    
    # Run the main async function
    loop.run_until_complete(main(app))
    
    # Clean up
    loop.close()

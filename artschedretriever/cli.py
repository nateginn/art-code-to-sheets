# artschedretriever/cli.py

import asyncio
from config import Config
from scheduler import ScheduleRetriever

async def main():
    config = Config()
    scheduler = ScheduleRetriever(config)
    
    try:
        await scheduler.navigate_to_agenda()
    except Exception as e:
        print(f"Error navigating to agenda: {e}")

if __name__ == "__main__":
    asyncio.run(main())

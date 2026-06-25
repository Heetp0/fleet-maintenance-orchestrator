import asyncio, json
from fleet_agents import app as fleet_app
from google.adk.runners import InMemoryRunner

async def main():
    runner = InMemoryRunner(app=fleet_app)
    runner.auto_create_session = True
    events = await runner.run_debug('query')
    if events:
        for event in events:
            print(event.__class__.__name__)
            if getattr(event, "type", None) == "run_completed":
                print(dir(event))
            if hasattr(event, "state"):
                print("Found state in event")
            if hasattr(event, "session_state"):
                print("Found session_state in event")

asyncio.run(main())

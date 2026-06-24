import sys
import asyncio
import os
from dotenv import load_dotenv

# Add the current directory to python path to import fleet_agents
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fleet_agents import app
from google.adk.runners import InMemoryRunner

# Load environment variables
load_dotenv()

async def run_cycle(cycle_number: int):
    print(f"=== Starting Fleet Maintenance Orchestrator for Cycle {cycle_number} ===")
    
    # Initialize Runner
    runner = InMemoryRunner(app=app)
    
    # Query for the agent
    query = f"Please ingest and analyze the telemetry data for cycle {cycle_number}, validate the RUL prediction, and if it's below 30 cycles, submit a maintenance ticket."
    
    try:
        # Run using run_debug
        response = await runner.run_debug(query)
        print("\n=== Final Response ===")
        print(response)
        print("=======================")
    except Exception as e:
        print(f"Error during agent execution: {e}")

if __name__ == "__main__":
    cycle = 38
    if len(sys.argv) > 1:
        try:
            cycle = int(sys.argv[1])
        except ValueError:
            print(f"Invalid cycle number. Using default cycle {cycle}.")
            
    asyncio.run(run_cycle(cycle))

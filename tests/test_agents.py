import os
import sys
import json
import time
import shutil
import asyncio
import threading
import unittest
import uvicorn
from multiprocessing import Process

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_agents import app
from google.adk.runners import InMemoryRunner
from mock_erp_server.server import app as fastapi_app, DB_FILE

class TestFleetAgentPipeline(unittest.TestCase):
    server_thread = None
    server_started = False
    
    @classmethod
    def setUpClass(cls):
        # Clean any old test artifacts
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
            except Exception:
                pass
                
        active_tickets_file = 'data/active_tickets.json'
        if os.path.exists(active_tickets_file):
            try:
                os.remove(active_tickets_file)
            except Exception:
                pass
                
        # Start mock ERP server in a separate thread
        def run_server():
            uvicorn.run(fastapi_app, host="127.0.0.1", port=8080, log_level="warning")
            
        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()
        # Give the server a moment to start up
        time.sleep(2.0)
        cls.server_started = True
        
    @classmethod
    def tearDownClass(cls):
        # Clean up database files
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
            except Exception:
                pass
        active_tickets_file = 'data/active_tickets.json'
        if os.path.exists(active_tickets_file):
            try:
                os.remove(active_tickets_file)
            except Exception:
                pass

    def setUp(self):
        # Ensure we have GEMINI_API_KEY set
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            self.skipTest("GEMINI_API_KEY is not set in environment variables. Skipping integration tests.")
            
    def test_end_to_end_orchestrator(self):
        # 1. Initialize the ADK InMemoryRunner
        runner = InMemoryRunner(app=app)
        
        # 2. Test healthy cycle (Cycle 10)
        # RUL should be high (~115+), so no maintenance ticket should be submitted.
        print("\n--- Testing healthy cycle 10 ---")
        query_healthy = "Please ingest and analyze the telemetry data for cycle 10, validate the RUL prediction, and if it's below 30 cycles, submit a maintenance ticket."
        
        loop = asyncio.get_event_loop()
        response_healthy = loop.run_until_complete(runner.run_debug(query_healthy))
        print("Healthy cycle response:")
        print(response_healthy)
        
        # Verify no ticket was written to FastAPI db
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r') as f:
                db_data = json.load(f)
                self.assertEqual(len(db_data), 0, "No tickets should be created for healthy cycles.")
                
        # 3. Test degraded cycle (Cycle 48)
        # RUL should be low (< 30 cycles) and sensors anomalous, which should trigger a ticket.
        print("\n--- Testing degraded cycle 48 ---")
        query_degraded = "Please ingest and analyze the telemetry data for cycle 48, validate the RUL prediction, and if it's below 30 cycles, submit a maintenance ticket."
        response_degraded = loop.run_until_complete(runner.run_debug(query_degraded))
        print("Degraded cycle response:")
        print(response_degraded)
        
        # Verify ticket was submitted to mock ERP
        self.assertTrue(os.path.exists(DB_FILE), "Ticket DB file should be created.")
        with open(DB_FILE, 'r') as f:
            db_data = json.load(f)
            self.assertEqual(len(db_data), 1, "One ticket should be logged in ERP system.")
            ticket = list(db_data.values())[0]
            self.assertEqual(ticket["engine_id"], "TF-804")
            self.assertEqual(ticket["priority_level"], "CRITICAL")
            
        # 4. Test duplicate prevention (Run Cycle 48 again)
        # It should detect the active ticket and skip submission.
        print("\n--- Testing duplicate ticket prevention (Cycle 48 again) ---")
        response_duplicate = loop.run_until_complete(runner.run_debug(query_degraded))
        print("Duplicate run response:")
        print(response_duplicate)
        
        # Verify we still only have 1 ticket in the ERP database (no new ticket was created)
        with open(DB_FILE, 'r') as f:
            db_data = json.load(f)
            self.assertEqual(len(db_data), 1, "ERP ticket database should still contain exactly 1 ticket (no duplicates).")

if __name__ == '__main__':
    unittest.main()

import os
import sys
import json
import time
import asyncio
import threading
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from google.genai import types

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_agents import app
from google.adk.runners import InMemoryRunner
from mock_erp_server.server import app as fastapi_app, DB_FILE

def create_mock_text_response(text: str) -> types.GenerateContentResponse:
    part = types.Part(text=text)
    content = types.Content(parts=[part], role="model")
    candidate = types.Candidate(
        content=content,
        finish_reason=types.FinishReason.STOP
    )
    usage = types.UsageMetadata(
        prompt_token_count=10,
        response_token_count=10,
        total_token_count=20
    )
    return types.GenerateContentResponse(
        candidates=[candidate],
        usage_metadata=usage,
        model_version="gemini-2.5-flash"
    )

def create_mock_tool_call_response(name: str, args: dict) -> types.GenerateContentResponse:
    func_call = types.FunctionCall(
        name=name,
        args=args,
        id="call_1"
    )
    part = types.Part(function_call=func_call)
    content = types.Content(parts=[part], role="model")
    candidate = types.Candidate(
        content=content,
        finish_reason=types.FinishReason.STOP
    )
    usage = types.UsageMetadata(
        prompt_token_count=10,
        response_token_count=10,
        total_token_count=20
    )
    return types.GenerateContentResponse(
        candidates=[candidate],
        usage_metadata=usage,
        model_version="gemini-2.5-flash"
    )

class TestFleetAgentPipelineMocked(unittest.TestCase):
    server_thread = None
    
    @classmethod
    def setUpClass(cls):
        # Clean any old test database files
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
            import uvicorn
            uvicorn.run(fastapi_app, host="127.0.0.1", port=8080, log_level="warning")
            
        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()
        time.sleep(2.0)
        
    @classmethod
    def tearDownClass(cls):
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

    @patch('google.genai.Client')
    def test_mocked_end_to_end_pipeline(self, mock_client_class):
        # Set up the mock GenAI Client and generate_content behavior
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Configure generate_content to return different values sequentially:
        # 1. RULAnalysisAgent response (Cycle 48 - RUL 12)
        # 2. RULGuardrailAgent response (Cycle 48 - CRITICAL)
        # 3. TicketingAgent response (Cycle 48 - Tool Call to submit_ticket)
        # 4. TicketingAgent response (Cycle 48 - Final text response summary)
        analysis_json = json.dumps({
            "engine_id": "TF-804",
            "cycle": 48,
            "estimated_rul": 12,
            "is_anomalous": True,
            "failing_sensors": ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure"],
            "status": "success"
        })
        
        guardrail_json = json.dumps({
            "validation_passed": True,
            "estimated_rul": 12,
            "failing_sensors": ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure"],
            "priority_level": "CRITICAL",
            "reasoning": "RUL is 12 cycles which is below safety threshold < 30. Multiple sensors are failing."
        })
        
        ticketing_args = {
            "engine_id": "TF-804",
            "failing_sensors": ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure"],
            "estimated_rul": 12,
            "priority_level": "CRITICAL"
        }
        
        ticketing_summary = "Submitted maintenance ticket MNT-9988 for engine TF-804 (Priority: CRITICAL, RUL: 12 cycles)."
        ticketing_skipped = "Ticket submission skipped: A ticket is already active for engine TF-804."
        
        # Mock the async method aio.models.generate_content using real GenerateContentResponse objects
        mock_client.aio.models.generate_content = AsyncMock()
        mock_client.aio.models.generate_content.side_effect = [
            create_mock_text_response(analysis_json),
            create_mock_text_response(guardrail_json),
            create_mock_tool_call_response("submit_ticket", ticketing_args),
            create_mock_text_response(ticketing_summary),
            create_mock_text_response(analysis_json),
            create_mock_text_response(guardrail_json),
            create_mock_tool_call_response("submit_ticket", ticketing_args),
            create_mock_text_response(ticketing_skipped)
        ]
        
        # Initialize InMemoryRunner with our app
        runner = InMemoryRunner(app=app)
        loop = asyncio.get_event_loop()
        
        # Run pipeline for cycle 48 (degraded cycle)
        query = "Analyze cycle 48"
        response = loop.run_until_complete(runner.run_debug(query))
        
        # Verify ticket was submitted to ERP DB
        self.assertTrue(os.path.exists(DB_FILE), "Ticket DB file should be created.")
        with open(DB_FILE, 'r') as f:
            db_data = json.load(f)
            self.assertEqual(len(db_data), 1, "Exactly one ticket should be in the ERP database.")
            ticket = list(db_data.values())[0]
            self.assertEqual(ticket["engine_id"], "TF-804")
            self.assertEqual(ticket["priority_level"], "CRITICAL")
            self.assertEqual(ticket["estimated_rul"], 12)
            self.assertEqual(ticket["failing_sensors"], ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure"])

        # Run again to check duplicate prevention
        response_dup = loop.run_until_complete(runner.run_debug(query))
        
        # Verify that still only 1 ticket is in the database
        with open(DB_FILE, 'r') as f:
            db_data = json.load(f)
            self.assertEqual(len(db_data), 1, "No new ticket should be created (duplicate prevention).")

if __name__ == '__main__':
    unittest.main()

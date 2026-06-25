import os
import sys
import json
import time
import socket
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

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ACTIVE_TICKETS_FILE = os.path.join(_PROJECT_ROOT, 'data', 'active_tickets.json')

# ERP server port — matches the URL in submit_ticket.py
_ERP_PORT = 8080


def _is_port_free(port: int) -> bool:
    """Return True if the given port is not currently in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


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
                
        if os.path.exists(_ACTIVE_TICKETS_FILE):
            try:
                os.remove(_ACTIVE_TICKETS_FILE)
            except Exception:
                pass
        # Note: no real ERP server needed — requests.post is patched inside the test
        
    @classmethod
    def tearDownClass(cls):
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
            except Exception:
                pass
        if os.path.exists(_ACTIVE_TICKETS_FILE):
            try:
                os.remove(_ACTIVE_TICKETS_FILE)
            except Exception:
                pass

    @patch('requests.post')
    @patch('google.genai.Client')
    def test_mocked_end_to_end_pipeline(self, mock_client_class, mock_requests_post):
        # Set up the mock GenAI Client and generate_content behavior
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock the ERP HTTP call so no real server is needed
        mock_erp_response = MagicMock()
        mock_erp_response.status_code = 201
        mock_erp_response.json.return_value = {
            "ticket_id": "MNT-9988",
            "engine_id": "TF-804",
            "failing_sensors": ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure"],
            "estimated_rul": 12,
            "priority_level": "CRITICAL",
            "status": "OPEN",
            "created_at": "2026-06-24T12:00:00"
        }
        mock_requests_post.return_value = mock_erp_response
        
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
            "engine_id": "TF-804",
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
        # run_debug() manages its own internal session automatically
        runner = InMemoryRunner(app=app)
        
        # Run pipeline for cycle 48 (degraded cycle)
        query = "Analyze cycle 48"
        events_first = asyncio.run(runner.run_debug(query))
        print(f"First run: {len(events_first)} events collected")
        
        # Verify ticket was submitted: check the agent-side active_tickets cache
        # (submit_ticket.py writes this file when the ERP call succeeds)
        self.assertTrue(os.path.exists(_ACTIVE_TICKETS_FILE),
                        "Agent-side active_tickets.json should be created after ticket submission.")
        with open(_ACTIVE_TICKETS_FILE, 'r') as f:
            active_data = json.load(f)
            self.assertIn("TF-804", active_data, "Ticket should be cached for engine TF-804.")
            cached = active_data["TF-804"]
            self.assertEqual(cached["ticket_id"], "MNT-9988")
            self.assertEqual(cached["priority_level"], "CRITICAL")

        # Run again to check duplicate prevention
        events_second = asyncio.run(runner.run_debug(query))
        print(f"Duplicate run: {len(events_second)} events collected")
        
        # Verify that requests.post was called exactly once (second run should hit
        # the local duplicate-prevention cache and never call ERP again)
        mock_requests_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()

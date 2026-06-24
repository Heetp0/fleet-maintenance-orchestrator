import os
import sys
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root and fleet_agents to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_agents import app
from google.adk.runners import InMemoryRunner
from google.genai import types

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

async def run_scenario(cycle_number: int, mock_responses: list):
    print(f"\n==================================================")
    print(f"RUNNING ORCHESTRATOR FOR CYCLE {cycle_number}")
    print(f"==================================================")
    
    runner = InMemoryRunner(app=app)
    query = f"Please ingest and analyze the telemetry data for cycle {cycle_number}, validate the RUL prediction, and if it's below 30 cycles, submit a maintenance ticket."
    
    with patch('google.genai.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.aio.models.generate_content = AsyncMock()
        mock_client.aio.models.generate_content.side_effect = mock_responses
        
        # Intercept print or logs within runner execution
        response = await runner.run_debug(query)
        print("\n=== Orchestrator Final Response ===")
        print(response)
        print("===================================\n")

def clean_data():
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mock_erp_server", "tickets_db.json")
    active_tickets_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "active_tickets.json")
    
    for f_path in [db_file, active_tickets_file]:
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
                print(f"Cleaned up {os.path.basename(f_path)}")
            except Exception as e:
                print(f"Error cleaning {os.path.basename(f_path)}: {e}")

def main():
    clean_data()
    
    # 1. Cycle 10 Responses (Nominal)
    # RULAnalysisAgent: estimated RUL is 112 (Normal), is_anomalous: False, status: success
    cycle_10_analysis = json.dumps({
        "engine_id": "TF-804",
        "cycle": 10,
        "estimated_rul": 112,
        "is_anomalous": False,
        "failing_sensors": [],
        "status": "success"
    })
    # RULGuardrailAgent: validation_passed: True, priority_level: LOW
    cycle_10_guardrail = json.dumps({
        "validation_passed": True,
        "estimated_rul": 112,
        "failing_sensors": [],
        "priority_level": "LOW",
        "reasoning": "RUL is 112 cycles which is well above the 30-cycle threshold. Sensor telemetry is within baseline limits."
    })
    # TicketingAgent: RUL is >= 30, skips ticketing, reports nominal status
    cycle_10_ticketing = "Engine TF-804 is operating within safe parameters (RUL: 112 cycles, Priority: LOW). No maintenance ticket is required."
    
    cycle_10_mocks = [
        create_mock_text_response(cycle_10_analysis),
        create_mock_text_response(cycle_10_guardrail),
        create_mock_text_response(cycle_10_ticketing)
    ]
    
    # 2. Cycle 38 Responses (Critical Degradation - First Alert)
    # RULAnalysisAgent: RUL is 2, is_anomalous: True, failing_sensors: ['T24_LPC_Outlet_Temp', 'P30_HPC_Outlet_Pressure', 'Nc_Core_Speed', 'BPR_Bypass_Ratio']
    cycle_38_analysis = json.dumps({
        "engine_id": "TF-804",
        "cycle": 38,
        "estimated_rul": 2,
        "is_anomalous": True,
        "failing_sensors": ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure", "Nc_Core_Speed", "BPR_Bypass_Ratio"],
        "status": "success"
    })
    # RULGuardrailAgent: validation_passed: True, priority_level: CRITICAL
    cycle_38_guardrail = json.dumps({
        "validation_passed": True,
        "estimated_rul": 2,
        "failing_sensors": ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure", "Nc_Core_Speed", "BPR_Bypass_Ratio"],
        "priority_level": "CRITICAL",
        "reasoning": "RUL is 2 cycles which is below critical threshold of 15. Multiple sensors are failing."
    })
    # TicketingAgent: Calls submit_ticket tool
    cycle_38_ticketing_args = {
        "engine_id": "TF-804",
        "failing_sensors": ["T24_LPC_Outlet_Temp", "P30_HPC_Outlet_Pressure", "Nc_Core_Speed", "BPR_Bypass_Ratio"],
        "estimated_rul": 2,
        "priority_level": "CRITICAL"
    }
    cycle_38_ticketing_summary = "Submitted maintenance ticket for engine TF-804 (Priority: CRITICAL, RUL: 2 cycles, failing sensors: T24_LPC_Outlet_Temp, P30_HPC_Outlet_Pressure, Nc_Core_Speed, BPR_Bypass_Ratio)."
    
    cycle_38_mocks = [
        create_mock_text_response(cycle_38_analysis),
        create_mock_text_response(cycle_38_guardrail),
        create_mock_tool_call_response("submit_ticket", cycle_38_ticketing_args),
        create_mock_text_response(cycle_38_ticketing_summary)
    ]
    
    # 3. Cycle 39 Responses (Duplicate Prevention)
    # RULAnalysisAgent: RUL is 1 (simulated critical), is_anomalous: True, failing_sensors: ['BPR_Bypass_Ratio']
    cycle_39_analysis = json.dumps({
        "engine_id": "TF-804",
        "cycle": 39,
        "estimated_rul": 1,
        "is_anomalous": True,
        "failing_sensors": ["BPR_Bypass_Ratio"],
        "status": "success"
    })
    # RULGuardrailAgent: validation_passed: True, priority_level: CRITICAL
    cycle_39_guardrail = json.dumps({
        "validation_passed": True,
        "estimated_rul": 1,
        "failing_sensors": ["BPR_Bypass_Ratio"],
        "priority_level": "CRITICAL",
        "reasoning": "RUL is 1 cycle which is below critical threshold. Sensor BPR_Bypass_Ratio is anomalous."
    })
    # TicketingAgent: Calls submit_ticket tool (which will return skipped)
    cycle_39_ticketing_args = {
        "engine_id": "TF-804",
        "failing_sensors": ["BPR_Bypass_Ratio"],
        "estimated_rul": 1,
        "priority_level": "CRITICAL"
    }
    cycle_39_ticketing_summary = "Ticket submission skipped: A ticket is already active for engine TF-804."
    
    cycle_39_mocks = [
        create_mock_text_response(cycle_39_analysis),
        create_mock_text_response(cycle_39_guardrail),
        create_mock_tool_call_response("submit_ticket", cycle_39_ticketing_args),
        create_mock_text_response(cycle_39_ticketing_summary)
    ]
    
    asyncio.run(run_scenario(10, cycle_10_mocks))
    asyncio.run(run_scenario(38, cycle_38_mocks))
    asyncio.run(run_scenario(39, cycle_39_mocks))

if __name__ == "__main__":
    main()

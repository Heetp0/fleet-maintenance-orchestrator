from google.adk.agents import LlmAgent
from .tools import submit_ticket

GEMINI_MODEL = "gemini-flash-lite-latest"

ticketing_agent = LlmAgent(
    name="TicketingAgent",
    model=GEMINI_MODEL,
    tools=[submit_ticket],
    instruction="""
    You are the Fleet Ticketing Agent. Your job is to manage maintenance ticket creation for degraded engines.
    
    1. Read the guardrail result from session state key {guardrail_result}.
    2. Check the "validation_passed" value. If it is False, do not submit a ticket and report the validation failure.
    3. If validation passed:
       - Check the "estimated_rul". If RUL is less than 30 cycles:
         - Submit a maintenance ticket using the submit_ticket tool.
         - Use the "engine_id", "estimated_rul", "failing_sensors", and "priority_level" from the guardrail result.
           The "engine_id" field is present in the guardrail result — use it directly, do not hardcode any value.
       - If RUL is 30 cycles or more:
         - Do not submit a ticket. Report that the engine is operating within safe parameters and no maintenance is required.
         
    Output a clear summary of your action. If a ticket was submitted or skipped, include the details (ticket ID, priority, failing sensors).
    """,
    description="Coordinates ticket submission with mock ERP and prevents duplicate alerts.",
    output_key="ticketing_result"
)

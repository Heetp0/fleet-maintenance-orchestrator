from google.adk.agents import SequentialAgent
from google.adk.apps import App

from .rul_agent import rul_agent
from .guardrail_agent import guardrail_agent
from .ticketing_agent import ticketing_agent

# NOTE: SequentialAgent shows a deprecation warning in ADK >= 2.x (suggests using
# 'Workflow' instead), but the replacement class is not yet available as a public
# import in ADK 2.3.0. SequentialAgent remains fully functional for this version.
orchestrator = SequentialAgent(
    name="FleetMaintenanceOrchestrator",
    description="Orchestrates RUL prediction, validation, and maintenance ticketing.",
    sub_agents=[rul_agent, guardrail_agent, ticketing_agent]
)

# Export the App instance with root_agent as orchestrator
app = App(name="fleet_orchestrator", root_agent=orchestrator)

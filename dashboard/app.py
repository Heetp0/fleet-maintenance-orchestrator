import streamlit as st
import asyncio
import sys
import os
import requests
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fleet_agents import app as fleet_app
from google.adk.runners import InMemoryRunner

st.set_page_config(page_title="✈️ Fleet Maintenance Orchestrator", page_icon="✈️", layout="wide")

def run_analysis(cycle_number: int, engine_id: str) -> dict:
    """Run the agent pipeline synchronously and return structured results."""
    async def _run():
        runner = InMemoryRunner(app=fleet_app)
        runner.auto_create_session = True
        query = f"Please ingest and analyze the telemetry data for engine {engine_id} at cycle {cycle_number}, validate the RUL prediction, and if it's below 30 cycles, submit a maintenance ticket."
        try:
            response = await runner.run_debug(query)
            
            import json
            rul_analysis_result = {}
            guardrail_result = {}
            ticketing_result = ""
            
            for event in response:
                if hasattr(event, 'content') and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text = part.text.strip()
                            if text.startswith("{") and text.endswith("}"):
                                try:
                                    data = json.loads(text)
                                    if "priority_level" in data:
                                        guardrail_result = data
                                    elif "estimated_rul" in data:
                                        rul_analysis_result = data
                                except Exception:
                                    pass
                            else:
                                ticketing_result = text

            return {
                "status": "success",
                "response": str(response),
                "rul_analysis_result": rul_analysis_result,
                "guardrail_result": guardrail_result,
                "ticketing_result": ticketing_result,
                "engine_id": engine_id,
                "cycle": cycle_number
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return asyncio.run(_run())

# --- Sidebar ---
st.sidebar.header("Fleet Controls")
engine_id = st.sidebar.selectbox("Select Engine", ["TF-804", "TF-201", "TF-512"])
cycle_number = st.sidebar.slider("Operational Cycle", 1, 50, 38)
run_btn = st.sidebar.button("▶ Run Analysis")

st.sidebar.divider()
st.sidebar.subheader("Natural Language Query")
query_text = st.sidebar.text_input("Ask the fleet agent...", placeholder="e.g. Check engine TF-804 at cycle 38")
send_btn = st.sidebar.button("Send")
st.sidebar.caption('Tip: Try "Check engine TF-512 at cycle 50"')

# Initialize state
if 'fleet_status' not in st.session_state:
    st.session_state.fleet_status = {
        "TF-804": {"rul": "— cycles", "delta": "Nominal"},
        "TF-201": {"rul": "— cycles", "delta": "Nominal"},
        "TF-512": {"rul": "— cycles", "delta": "Nominal"}
    }
if 'last_run' not in st.session_state:
    st.session_state.last_run = None

# --- Main area ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="TF-804", value=st.session_state.fleet_status["TF-804"]["rul"], delta=st.session_state.fleet_status["TF-804"]["delta"], delta_color="inverse")
with col2:
    st.metric(label="TF-201", value=st.session_state.fleet_status["TF-201"]["rul"], delta=st.session_state.fleet_status["TF-201"]["delta"], delta_color="inverse")
with col3:
    st.metric(label="TF-512", value=st.session_state.fleet_status["TF-512"]["rul"], delta=st.session_state.fleet_status["TF-512"]["delta"], delta_color="inverse")

# Actions
do_run = False
target_engine = None
target_cycle = None

if run_btn:
    do_run = True
    target_engine = engine_id
    target_cycle = cycle_number

if send_btn and query_text:
    engine_match = re.search(r'TF-\d+', query_text)
    cycle_match = re.search(r'\d+', query_text.replace(engine_match.group(0), '') if engine_match else query_text)
    
    if engine_match and cycle_match:
        do_run = True
        target_engine = engine_match.group(0)
        target_cycle = int(cycle_match.group(0))
    else:
        st.warning("Could not parse engine ID or cycle number from query. Try: 'Check engine TF-804 at cycle 38'")

if do_run and target_engine and target_cycle:
    with st.spinner(f"Running analysis for {target_engine} at cycle {target_cycle}..."):
        result = run_analysis(target_cycle, target_engine)
        
        if result.get("status") == "success":
            rul_res = result.get("rul_analysis_result", {})
            guardrail_res = result.get("guardrail_result", {})
            
            rul = rul_res.get("estimated_rul", "Error")
            priority = guardrail_res.get("priority_level", "Nominal")
            
            if target_engine in st.session_state.fleet_status:
                st.session_state.fleet_status[target_engine] = {
                    "rul": f"{rul} cycles" if isinstance(rul, int) else "— cycles",
                    "delta": priority if priority != "LOW" else "Nominal",
                }
            st.session_state.last_run = result
            st.rerun()
        else:
            st.error(f"Error during analysis: {result.get('error')}")

# Display Results
last_run = st.session_state.last_run
if last_run:
    rul_res = last_run.get("rul_analysis_result", {})
    guardrail_res = last_run.get("guardrail_result", {})
    ticket_res = last_run.get("ticketing_result", "")
    eng = last_run.get("engine_id")
    cyc = last_run.get("cycle")
    
    st.subheader(f"Engine {eng} - Cycle {cyc}")
    
    if guardrail_res and "reasoning" in guardrail_res:
        st.info(f"**🛡️ Guardrail Verdict:** {guardrail_res['reasoning']}")
    
    priority = guardrail_res.get("priority_level", "LOW")
    if priority in ["CRITICAL", "HIGH"]:
        st.error(ticket_res)
    elif priority == "MEDIUM":
        st.warning(ticket_res)
    else:
        st.success(ticket_res)
        
    with st.expander("Raw Analysis JSON"):
        st.json(rul_res)

# Open Tickets Panel
st.divider()
st.subheader("Open Maintenance Tickets")

try:
    resp = requests.get("http://127.0.0.1:8080/api/v1/maintenance/tickets")
    if resp.status_code == 200:
        tickets = resp.json()
        if not tickets:
            st.success("No open tickets")
        else:
            for t in tickets:
                priority = t.get("priority_level", "LOW")
                card_text = f"**Ticket ID:** {t.get('ticket_id')} | **Engine:** {t.get('engine_id')} | **Priority:** {priority} | **RUL:** {t.get('estimated_rul')} | **Sensors:** {', '.join(t.get('failing_sensors', []))} | **Created:** {t.get('created_at')}"
                if priority == "CRITICAL":
                    st.error(card_text)
                elif priority in ["HIGH", "MEDIUM"]:
                    st.warning(card_text)
                else:
                    st.info(card_text)
    else:
        st.warning("Could not fetch tickets")
except requests.exceptions.ConnectionError:
    st.warning("ERP server offline — start mock_erp_server/server.py")

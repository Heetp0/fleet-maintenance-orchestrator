import os
import json
import requests

# Resolve the active tickets file path relative to this file's location,
# with a CWD fallback — consistent with the other tools in this package.
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_TOOLS_DIR, '..', '..'))

ACTIVE_TICKETS_FILE = os.path.join(_PROJECT_ROOT, 'data', 'active_tickets.json')

def submit_ticket(
    engine_id: str,
    failing_sensors: list[str],
    estimated_rul: int,
    priority_level: str
) -> dict:
    """
    Submits a maintenance ticket to the mock ERP system. If a ticket is already active 
    for the engine, it returns the existing ticket to prevent duplicate alerting.
    
    Args:
        engine_id: The ID of the degraded engine (e.g. 'TF-804')
        failing_sensors: List of sensors that exceeded limits
        estimated_rul: Estimated Remaining Useful Life in cycles
        priority_level: Priority level (LOW, MEDIUM, HIGH, CRITICAL)
        
    Returns:
        dict: The response from the ERP system, including the ticket_id and status.
    """
    data_dir = os.path.join(_PROJECT_ROOT, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # 1. Read existing tickets database to prevent duplicates
    active_tickets = {}
    if os.path.exists(ACTIVE_TICKETS_FILE):
        try:
            with open(ACTIVE_TICKETS_FILE, 'r') as f:
                active_tickets = json.load(f)
        except Exception:
            active_tickets = {}
            
    # Check if a ticket already exists and is not resolved
    if engine_id in active_tickets:
        existing = active_tickets[engine_id]
        print(f"Duplicate alert prevented. Engine {engine_id} already has active ticket {existing['ticket_id']}.")
        return {
            "status": "skipped",
            "reason": "Ticket already exists for this engine",
            "ticket_id": existing["ticket_id"],
            "engine_id": engine_id,
            "priority_level": existing["priority_level"],
            "created_at": existing["created_at"]
        }
        
    # 2. Call mock ERP API
    url = "http://127.0.0.1:8080/api/v1/maintenance/ticket"
    payload = {
        "engine_id": engine_id,
        "failing_sensors": failing_sensors,
        "estimated_rul": estimated_rul,
        "priority_level": priority_level
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 201:
            res_json = response.json()
            res_json["status"] = "success"
            
            # Save ticket to active tickets DB (agent-side duplicate prevention cache)
            active_tickets[engine_id] = {
                "ticket_id": res_json["ticket_id"],
                "priority_level": priority_level,
                "created_at": res_json["created_at"]
            }
            with open(ACTIVE_TICKETS_FILE, 'w') as f:
                json.dump(active_tickets, f, indent=4)
                
            return res_json
        else:
            return {
                "status": "error",
                "error_message": f"ERP server returned status code {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to connect to ERP server: {str(e)}"
        }

import os
import json
import uuid
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Mock ERP Fleet Maintenance API", version="1.0.0")

DB_FILE = os.path.join(os.path.dirname(__file__), "tickets_db.json")

class TicketCreate(BaseModel):
    engine_id: str = Field(..., description="Unique identifier of the failing engine")
    failing_sensors: List[str] = Field(..., description="List of sensors exceeding control limits")
    estimated_rul: int = Field(..., description="Estimated remaining useful cycles before failure")
    priority_level: str = Field(..., description="Priority level (LOW, MEDIUM, HIGH, CRITICAL)")

class TicketResponse(TicketCreate):
    ticket_id: str
    status: str
    created_at: str

def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(db: dict):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

@app.post("/api/v1/maintenance/ticket", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket: TicketCreate):
    # Validate priority level
    priority = ticket.priority_level.upper()
    if priority not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Priority level must be one of: LOW, MEDIUM, HIGH, CRITICAL"
        )
        
    db = load_db()
    
    # Check if a ticket already exists for this engine
    # Wait, the prompt state management should also prevent this at the agent level,
    # but the API can return the existing ticket if requested, or just log a new one.
    # Let's allow creating multiple tickets but keep track of them.
    ticket_id = f"MNT-{uuid.uuid4().hex[:8].upper()}"
    import datetime
    created_at = datetime.datetime.now().isoformat()
    
    new_ticket = TicketResponse(
        ticket_id=ticket_id,
        engine_id=ticket.engine_id,
        failing_sensors=ticket.failing_sensors,
        estimated_rul=ticket.estimated_rul,
        priority_level=priority,
        status="OPEN",
        created_at=created_at
    )
    
    db[ticket_id] = new_ticket.model_dump()
    save_db(db)
    
    print(f"Logged new ticket {ticket_id} for engine {ticket.engine_id} (RUL: {ticket.estimated_rul})")
    return new_ticket

@app.get("/api/v1/maintenance/tickets", response_model=List[TicketResponse])
def get_tickets():
    db = load_db()
    return list(db.values())

@app.delete("/api/v1/maintenance/tickets/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_tickets():
    save_db({})
    return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)

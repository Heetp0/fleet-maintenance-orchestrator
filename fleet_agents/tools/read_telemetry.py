import pandas as pd
import os

def read_telemetry(cycle_number: int) -> dict:
    """
    Reads the turbofan telemetry data for a specific operational cycle of engine TF-804.
    
    Args:
        cycle_number: The operational cycle to retrieve telemetry for (1 to 50).
        
    Returns:
        dict: A dictionary containing the telemetry values for the specified cycle, 
              including operational settings and 5 key sensors, or an error status.
    """
    csv_path = 'data/telemetry_TF804.csv'
    if not os.path.exists(csv_path):
        # Fallback for running from parent or other directories
        csv_path = os.path.join(os.path.dirname(__file__), '../../data/telemetry_TF804.csv')
    
    if not os.path.exists(csv_path):
        return {"status": "error", "error_message": f"Telemetry file not found at {csv_path}"}
        
    try:
        df = pd.read_csv(csv_path)
        row = df[df['Cycle'] == cycle_number]
        if row.empty:
            return {"status": "error", "error_message": f"Cycle {cycle_number} not found in telemetry"}
            
        data = row.iloc[0].to_dict()
        data["status"] = "success"
        return data
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

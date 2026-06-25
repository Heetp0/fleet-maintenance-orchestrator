import pandas as pd
import os

def read_telemetry(cycle_number: int, engine_id: str = "TF-804") -> dict:
    """
    Reads the turbofan telemetry data for a specific engine and operational cycle.

    Args:
        cycle_number: The operational cycle to retrieve telemetry for (1 to 50).
        engine_id: The engine identifier (e.g. 'TF-804'). Defaults to 'TF-804'.

    Returns:
        dict: A dictionary containing the telemetry values for the specified cycle,
              including operational settings and 5 key sensors, or an error status.
    """
    csv_filename = f"telemetry_{engine_id.replace('-', '')}.csv"
    csv_path = os.path.join('data', csv_filename)

    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', csv_filename)

    if not os.path.exists(csv_path):
        return {"status": "error", "error_message": f"Telemetry file not found for engine {engine_id} at {csv_path}"}

    try:
        df = pd.read_csv(csv_path)
        row = df[df['Cycle'] == cycle_number]
        if row.empty:
            return {"status": "error", "error_message": f"Cycle {cycle_number} not found in telemetry for engine {engine_id}"}
        data = row.iloc[0].to_dict()
        data["status"] = "success"
        return data
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

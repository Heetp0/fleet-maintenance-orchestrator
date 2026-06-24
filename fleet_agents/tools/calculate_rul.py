import os
import pickle
import pandas as pd

# Module-level cache — model is loaded from disk only once per process lifetime.
_model = None

def _get_model():
    """Load and cache the RUL model at module level to avoid repeated disk I/O."""
    global _model
    if _model is not None:
        return _model, None  # (model, error)

    model_path = 'models/rul_model.pkl'
    if not os.path.exists(model_path):
        model_path = os.path.join(os.path.dirname(__file__), '../../models/rul_model.pkl')

    if not os.path.exists(model_path):
        return None, f"ML model file not found at {model_path}"

    try:
        with open(model_path, 'rb') as f:
            _model = pickle.load(f)
        return _model, None
    except Exception as e:
        return None, str(e)


def calculate_rul(
    setting_1: float,
    setting_2: float,
    setting_3: float,
    sensor_2: float,
    sensor_11: float,
    sensor_9: float,
    sensor_8: float,
    sensor_15: float
) -> dict:
    """
    Uses the trained predictive ML model to estimate the Remaining Useful Life (RUL)
    of the turbofan engine based on the current cycle's operational settings and sensor readings.
    
    Args:
        setting_1: Altitude / operational setting 1
        setting_2: Mach Number / operational setting 2
        setting_3: Throttle Resolver Angle / operational setting 3
        sensor_2: LPC Outlet Temperature (T24)
        sensor_11: Static Pressure at HPC outlet (Ps30)
        sensor_9: Fan Speed (Nf)
        sensor_8: Core Speed (Nc)
        sensor_15: Bypass Ratio (BPR)
        
    Returns:
        dict: A dictionary containing the estimated remaining useful cycles (RUL) and status.
    """
    model, error = _get_model()
    if error:
        return {"status": "error", "error_message": error}

    try:
        # Create a single-row DataFrame for prediction
        input_data = pd.DataFrame([[
            setting_1, setting_2, setting_3,
            sensor_2, sensor_11, sensor_9, sensor_8, sensor_15
        ]], columns=[
            'setting_1', 'setting_2', 'setting_3',
            'sensor_2', 'sensor_11', 'sensor_9', 'sensor_8', 'sensor_15'
        ])
        
        prediction = model.predict(input_data)[0]
        estimated_rul = int(round(prediction))
        
        return {
            "status": "success",
            "estimated_rul": estimated_rul
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

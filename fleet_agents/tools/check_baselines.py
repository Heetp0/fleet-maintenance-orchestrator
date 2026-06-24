import os
import json

def check_baselines(
    t24: float,
    p30: float,
    nf: float,
    nc: float,
    bpr: float
) -> dict:
    """
    Compares the current sensor readings against the upper and lower control limits (baselines)
    to identify any sensor anomalies.
    
    Args:
        t24: LPC Outlet Temperature (T24_LPC_Outlet_Temp)
        p30: Static Pressure at HPC outlet (P30_HPC_Outlet_Pressure)
        nf: Fan Speed (Nf_Fan_Speed)
        nc: Core Speed (Nc_Core_Speed)
        bpr: Bypass Ratio (BPR_Bypass_Ratio)
        
    Returns:
        dict: A dictionary containing the lists of exceeded/anomalous sensors and status.
    """
    baselines_path = 'data/sensor_baselines.json'
    if not os.path.exists(baselines_path):
        baselines_path = os.path.join(os.path.dirname(__file__), '../../data/sensor_baselines.json')
        
    if not os.path.exists(baselines_path):
        return {"status": "error", "error_message": "Baselines file not found"}
        
    try:
        with open(baselines_path, 'r') as f:
            baselines = json.load(f)
            
        anomalies = []
        readings = {
            "T24_LPC_Outlet_Temp": t24,
            "P30_HPC_Outlet_Pressure": p30,
            "Nf_Fan_Speed": nf,
            "Nc_Core_Speed": nc,
            "BPR_Bypass_Ratio": bpr
        }
        
        for sensor_name, val in readings.items():
            limits = baselines.get(sensor_name)
            if limits:
                lcl = limits["LCL"]
                ucl = limits["UCL"]
                if val < lcl or val > ucl:
                    anomalies.append({
                        "sensor": sensor_name,
                        "value": val,
                        "lcl": lcl,
                        "ucl": ucl,
                        "reason": f"Value {val:.4f} is outside range [{lcl}, {ucl}]"
                    })
                    
        return {
            "status": "success",
            "is_anomalous": len(anomalies) > 0,
            "failing_sensors": [a["sensor"] for a in anomalies],
            "anomalies_details": anomalies
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

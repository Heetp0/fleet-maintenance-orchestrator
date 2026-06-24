import os
import json
import numpy as np
import pandas as pd

def generate_telemetry():
    np.random.seed(42)
    cycles = np.arange(1, 51)
    n_cycles = len(cycles)
    
    # Operational settings matching FD001 (sea level, very small variations)
    altitude = np.random.normal(-0.0007, 0.001, n_cycles)
    mach_number = np.random.normal(-0.0004, 0.0002, n_cycles)
    throttle = np.random.normal(100.0, 0.01, n_cycles)
    
    # Sensors (matching FD001 scales)
    # 1. Total Temperature at LPC outlet (K) - T24 (Sensor 2)
    t24 = 641.8 + 0.02 * cycles + np.random.normal(0, 0.15, n_cycles)
    
    # 2. Static Pressure at HPC outlet (psia) - P30 (Sensor 11)
    p30 = 47.45 + 0.006 * cycles + np.random.normal(0, 0.05, n_cycles)
    
    # 3. Fan Speed (rpm) - Nf (Sensor 9 - wait, let's use BPR/Sensor 15 as sensor 5)
    # Fan speed Nf in FD001 is Sensor 9 (around 9046). Let's make it decrease.
    nf = 9046.0 - 0.5 * cycles + np.random.normal(0, 10.0, n_cycles)
    
    # 4. Core Speed (rpm) - Nc (Sensor 8)
    nc = 2388.05 + 0.003 * cycles + np.random.normal(0, 0.03, n_cycles)
    
    # 5. Bypass Ratio - BPR (Sensor 15)
    bpr = 8.41 + 0.002 * cycles + np.random.normal(0, 0.01, n_cycles)
    
    # Introduce anomalous spikes at cycle 38 and 44
    # Anomalous spike 1: cycle 38
    idx_38 = 37  # 0-indexed for cycle 38
    t24[idx_38] += 1.8      # Large positive spike
    p30[idx_38] += 0.5      # Large pressure spike
    nc[idx_38] += 0.18      # Core speed spike
    
    # Anomalous spike 2: cycle 44
    idx_44 = 43  # 0-indexed for cycle 44
    t24[idx_44] += 2.2      # Large positive spike
    p30[idx_44] += 0.6      # Large pressure spike
    nc[idx_44] += 0.22      # Core speed spike
    
    # Create DataFrame
    df = pd.DataFrame({
        'Engine_ID': ['TF-804'] * n_cycles,
        'Cycle': cycles,
        'Altitude': altitude,
        'Mach_Number': mach_number,
        'Throttle_Resolver_Angle': throttle,
        'T24_LPC_Outlet_Temp': t24,
        'P30_HPC_Outlet_Pressure': p30,
        'Nf_Fan_Speed': nf,
        'Nc_Core_Speed': nc,
        'BPR_Bypass_Ratio': bpr
    })
    
    # Save CSV
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/telemetry_TF804.csv', index=False)
    print("Generated data/telemetry_TF804.csv")

def generate_baselines():
    # Define upper and lower control limits (UCL, LCL) for reasoning
    baselines = {
        "T24_LPC_Outlet_Temp": {
            "LCL": 640.0,
            "UCL": 643.0
        },
        "P30_HPC_Outlet_Pressure": {
            "LCL": 47.2,
            "UCL": 47.85
        },
        "Nf_Fan_Speed": {
            "LCL": 8980.0,
            "UCL": 9070.0
        },
        "Nc_Core_Speed": {
            "LCL": 2387.9,
            "UCL": 2388.2
        },
        "BPR_Bypass_Ratio": {
            "LCL": 8.38,
            "UCL": 8.48
        }
    }
    
    with open('data/sensor_baselines.json', 'w') as f:
        json.dump(baselines, f, indent=4)
    print("Generated data/sensor_baselines.json")

def generate_erp_schema():
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "MaintenanceTicket",
        "type": "object",
        "properties": {
            "engine_id": {
                "type": "string",
                "description": "Unique identifier of the failing engine"
            },
            "failing_sensors": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of sensors exceeding baseline control limits"
            },
            "estimated_rul": {
                "type": "integer",
                "description": "Estimated remaining useful cycles before failure"
            },
            "priority_level": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                "description": "Priority tier based on remaining useful life"
            }
        },
        "required": ["engine_id", "failing_sensors", "estimated_rul", "priority_level"]
    }
    
    with open('data/erp_api_schema.json', 'w') as f:
        json.dump(schema, f, indent=4)
    print("Generated data/erp_api_schema.json")

if __name__ == '__main__':
    generate_telemetry()
    generate_baselines()
    generate_erp_schema()

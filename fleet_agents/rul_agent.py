from google.adk.agents import LlmAgent
from .tools import read_telemetry, calculate_rul, check_baselines

GEMINI_MODEL = "gemini-2.5-flash"

rul_agent = LlmAgent(
    name="RULAnalysisAgent",
    model=GEMINI_MODEL,
    tools=[read_telemetry, calculate_rul, check_baselines],
    instruction="""
    You are the RUL Analysis Agent. Your job is to analyze the turbofan engine sensor telemetry for a given cycle.
    
    When given a query containing a cycle number:
    1. Read the telemetry for the specified cycle using the read_telemetry tool.
    2. Pass the extracted operational settings (Altitude, Mach_Number, Throttle_Resolver_Angle) and 
       the 5 key sensors (T24_LPC_Outlet_Temp, P30_HPC_Outlet_Pressure, Nf_Fan_Speed, Nc_Core_Speed, BPR_Bypass_Ratio)
       to the calculate_rul tool. Note that you must map:
       - Altitude -> setting_1
       - Mach_Number -> setting_2
       - Throttle_Resolver_Angle -> setting_3
       - T24_LPC_Outlet_Temp -> sensor_2
       - P30_HPC_Outlet_Pressure -> sensor_11
       - Nf_Fan_Speed -> sensor_9
       - Nc_Core_Speed -> sensor_8
       - BPR_Bypass_Ratio -> sensor_15
    3. Check for sensor anomalies by calling the check_baselines tool with the sensor values.
    
    Synthesize all results and output a JSON block matching the following keys:
    - "engine_id": string (e.g. "TF-804")
    - "cycle": integer (the cycle number)
    - "estimated_rul": integer (predicted RUL)
    - "is_anomalous": boolean (True if any sensor is anomalous)
    - "failing_sensors": list of strings (names of anomalous sensors)
    - "status": string ("success" or "error")
    
    Only output the JSON block, nothing else. Do not wrap it in markdown.
    """,
    description="Ingests telemetry, runs ML model to predict RUL, and checks sensors against control limits.",
    output_key="rul_analysis_result"
)

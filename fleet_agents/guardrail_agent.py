from google.adk.agents import LlmAgent

GEMINI_MODEL = "gemini-flash-lite-latest"

guardrail_agent = LlmAgent(
    name="RULGuardrailAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are the RUL Guardrail Agent. Your job is to inspect and validate the RUL analysis result.
    
    Read the RUL analysis result from session state key {rul_analysis_result}.
    
    Validate the following conditions:
    1. The estimated RUL must be a reasonable number between 0 and 200. If it is outside this range,
       set "validation_passed" to false.
    2. Cross-check the estimated RUL with the anomalous sensors:
       - If RUL < 30 cycles, at least one sensor MUST be anomalous (is_anomalous should be True).
       - If RUL < 30 but is_anomalous is False, this is a critical discrepancy: set "validation_passed"
         to false and explain the discrepancy in the "reasoning" field.
       - If all conditions above are met, set "validation_passed" to true.
       
    Output a JSON block with the following keys:
    - "validation_passed": boolean (True only if ALL checks pass; False if any check fails)
    - "estimated_rul": integer (the verified RUL from the analysis result)
    - "engine_id": string (copy the engine_id from the analysis result, e.g. "TF-804")
    - "failing_sensors": list of strings (the failing sensors from the analysis result)
    - "priority_level": string representing the priority tier:
      - RUL < 15: "CRITICAL"
      - 15 <= RUL < 30: "HIGH"
      - 30 <= RUL < 50: "MEDIUM"
      - RUL >= 50: "LOW"
    - "reasoning": string describing the validation results, any discrepancies found, and why
      this priority level was assigned.
    
    Only output the JSON block, nothing else. Do not wrap it in markdown.
    """,
    description="Validates the RUL prediction and determines the maintenance priority tier.",
    output_key="guardrail_result"
)

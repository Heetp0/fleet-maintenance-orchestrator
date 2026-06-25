# ✈️ Fleet Maintenance Orchestrator

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.3.0-4285F4?logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![Model](https://img.shields.io/badge/ML%20Model-Random%20Forest-orange?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Kaggle Capstone](https://img.shields.io/badge/Kaggle-Agents%20for%20Business%20Capstone-20BEFF?logo=kaggle&logoColor=white)](https://www.kaggle.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An autonomous multi-agent system for predictive turbofan engine maintenance and automated AOG ticket dispatch. Built for the Google × Kaggle **"Agents for Business"** capstone project using the [Google Agent Development Kit (ADK) 2.0](https://google.github.io/adk-docs/).

---

## The Problem

**Aircraft on Ground (AOG)** events — unscheduled groundings caused by unexpected engine failure — cost airlines between \$150,000 and \$500,000 per hour per aircraft. Traditional reactive maintenance discovers failures after they happen. Predictive maintenance discovers them before they happen, but the data science pipeline is typically manual: an engineer pulls telemetry, runs a model, reads the output, and files a ticket.

This project replaces that manual chain with a fully autonomous workflow.

---

## What It Does

The orchestrator monitors live turbofan engine sensor telemetry, predicts the **Remaining Useful Life (RUL)** of an engine in operational cycles, validates the prediction against physical baselines, and autonomously dispatches a prioritised maintenance ticket to an Enterprise Resource Planning (ERP) system — all without human intervention in the loop.

```
Live sensor telemetry → RUL prediction → Safety validation → ERP ticket dispatch
```

If a ticket already exists for an engine, the system detects the duplicate and suppresses further alerts. If the engine is healthy, no ticket is created.

---

## Architecture

The system is split into two distinct halves that each do what they are best at.

### Half 1 — Predictive Calculator (Traditional ML)

A **Random Forest Regression** model, trained offline on the NASA CMAPSS turbofan degradation dataset, serves as a pure mathematical tool. It accepts eight features from live sensor telemetry and outputs a single value: the predicted RUL in cycles.

| Metric | Value |
|---|---|
| Dataset | NASA CMAPSS — FD001 sub-dataset |
| Features | 3 operational settings + 5 key sensors |
| RUL cap | 125 cycles (standard CMAPSS convention) |
| Validation split | 80 / 20 |
| **RMSE** | **19.87 cycles** |
| **MAE** | **14.39 cycles** |
| **R² Score** | **0.7674 (76.74%)** |

### Half 2 — Autonomous Orchestrator (Multi-Agent System)

A **SequentialAgent** pipeline built with Google ADK manages the operational workflow. It delegates tasks across three specialised sub-agents:

```
┌─────────────────────────────────────────────────────────┐
│                FleetMaintenanceOrchestrator              │
│                   (SequentialAgent)                     │
│                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐ │
│  │  RUL Analysis │→ │   Guardrail   │→ │  Ticketing  │ │
│  │     Agent     │  │     Agent     │  │    Agent    │ │
│  └───────────────┘  └───────────────┘  └─────────────┘ │
│         ↓                  ↓                  ↓         │
│  read_telemetry     LLM-as-a-judge      submit_ticket   │
│  calculate_rul      Validates RUL vs.   Dedup check →   │
│  check_baselines    sensor anomalies    POST to ERP      │
└─────────────────────────────────────────────────────────┘
```

**RUL Analysis Agent** — Ingests raw telemetry for a given cycle, invokes the ML model to calculate RUL, and cross-checks all five monitored sensors against statistical control limits. Outputs a structured JSON result to session state.

**Guardrail Agent (LLM-as-a-judge)** — Acts as an independent inspector. It reads the RUL analysis result and validates two rules: the predicted RUL must be physically plausible (0–200 cycles), and if RUL is below 30 cycles, at least one sensor must be flagging an anomaly. This prevents false alarms from model drift or hallucinated data. It also assigns a priority tier:

| RUL | Priority |
|---|---|
| < 15 cycles | CRITICAL |
| 15 – 29 cycles | HIGH |
| 30 – 49 cycles | MEDIUM |
| ≥ 50 cycles | LOW |

**Ticketing Agent** — Reads the validated guardrail result. If the engine is degrading past the 30-cycle threshold, it checks local state to prevent duplicate alerts, then POSTs a structured maintenance ticket to the ERP system. If the engine is healthy, it reports nominal status and takes no action.

---

## Project Structure

```
fleet-maintenance-orchestrator/
│
├── fleet_agents/               # ADK agent definitions
│   ├── agent.py                # SequentialAgent orchestrator + App export
│   ├── rul_agent.py            # RUL Analysis Agent
│   ├── guardrail_agent.py      # Guardrail / validation Agent
│   ├── ticketing_agent.py      # ERP Ticketing Agent
│   └── tools/
│       ├── read_telemetry.py   # Reads cycle row from CSV
│       ├── calculate_rul.py    # Invokes Random Forest model
│       ├── check_baselines.py  # Sensor anomaly detection
│       └── submit_ticket.py    # Dedup check + ERP POST
│
├── mock_erp_server/
│   └── server.py               # FastAPI mock ERP (ticket CRUD)
│
├── data/
│   ├── telemetry_TF804.csv     # Synthetic 50-cycle engine telemetry
│   └── sensor_baselines.json   # Statistical control limits (LCL/UCL)
│
├── models/
│   └── rul_model.pkl           # Trained Random Forest regressor
│
├── tests/
│   └── test_tools.py           # Unit tests for all four tools
│
├── train_rul_model.py          # Model training + evaluation script
├── run_orchestrator.py         # Pipeline entry point
├── requirements.txt
└── .env.example
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent framework | Google ADK 2.3.0 |
| LLM backend | Gemini 2.5 Flash |
| ML model | Scikit-learn Random Forest Regressor |
| Mock ERP API | FastAPI + Uvicorn |
| Data processing | Pandas, NumPy |
| Runtime | Python 3.12 |

---

## Setup and Installation

**Prerequisites:** Python 3.12, a Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey)).

**1. Clone the repository:**

```bash
git clone https://github.com/Heetp0/fleet-maintenance-orchestrator.git
cd fleet-maintenance-orchestrator
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Configure your API key:**

Copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env
```

```env
GEMINI_API_KEY="your_api_key_here"
```

---

## Usage

The pipeline requires two terminal windows running simultaneously.

**Terminal 1 — Start the Mock ERP Server:**

```bash
python mock_erp_server/server.py
```

The server starts on `http://127.0.0.1:8080`. You can view all filed tickets at `http://127.0.0.1:8080/api/v1/maintenance/tickets`.

**Terminal 2 — Run the Orchestrator:**

```bash
# Healthy engine (cycle 10) — no ticket should be created
python run_orchestrator.py 10

# Degrading engine (cycle 38) — CRITICAL ticket should be dispatched
python run_orchestrator.py 38

# Run cycle 38 a second time — duplicate ticket should be suppressed
python run_orchestrator.py 38
```

---

## Running the Dashboard

The Streamlit dashboard provides a visual fleet overview, real-time analysis results, and a natural language query interface.

**Terminal 1 — Start the Mock ERP Server:**
```bash
python mock_erp_server/server.py
```

**Terminal 2 — Launch the Dashboard:**
```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501` in your browser. Select an engine and cycle from the sidebar and click **▶ Run Analysis**, or type a natural language query such as `Check engine TF-512 at cycle 50`.

---

## Demo Output

### Nominal Engine — Cycle 10

The RUL is predicted at **110 cycles**. No sensors are anomalous. The guardrail passes validation. No ticket is created.

```
=== Starting Fleet Maintenance Orchestrator for Cycle 10 ===

RULAnalysisAgent > {
  "engine_id": "TF-804",
  "cycle": 10,
  "estimated_rul": 110,
  "is_anomalous": false,
  "failing_sensors": [],
  "status": "success"
}

RULGuardrailAgent > {
  "validation_passed": true,
  "estimated_rul": 110,
  "priority_level": "LOW",
  "reasoning": "The engine is operating within nominal parameters."
}

TicketingAgent > RUL of 110 cycles is well above the 30-cycle threshold.
No maintenance ticket has been submitted. The engine is operating safely.
```

### Degrading Engine — Cycle 38

The RUL is predicted at **2 cycles**. Four sensors are breaching control limits. The guardrail classifies this as CRITICAL. A ticket is dispatched to the ERP.

```
=== Starting Fleet Maintenance Orchestrator for Cycle 38 ===

RULAnalysisAgent > {
  "engine_id": "TF-804",
  "cycle": 38,
  "estimated_rul": 2,
  "is_anomalous": true,
  "failing_sensors": [
    "T24_LPC_Outlet_Temp",
    "P30_HPC_Outlet_Pressure",
    "Nc_Core_Speed",
    "BPR_Bypass_Ratio"
  ]
}

RULGuardrailAgent > {
  "validation_passed": true,
  "priority_level": "CRITICAL",
  "reasoning": "RUL < 15 cycles with 4 confirmed sensor anomalies."
}

Logged new ticket MNT-9BD6EAD1 for engine TF-804 (RUL: 2)
POST /api/v1/maintenance/ticket → 201 Created

TicketingAgent > Ticket MNT-9BD6EAD1 dispatched. Priority: CRITICAL.
```

### Duplicate Suppression

Running cycle 38 a second time returns the existing ticket ID and takes no further action:

```
Duplicate alert prevented. Engine TF-804 already has active ticket MNT-9BD6EAD1.
TicketingAgent > Ticket already active for TF-804. No new ticket submitted.
```

---

## Running Tests

Unit tests cover all four tool functions and include mocked ERP responses:

```bash
python -m pytest tests/ -v
```

---

## Monitored Sensors and Baselines

The guardrail evaluates five sensors from the CMAPSS feature set:

| Sensor | Parameter | LCL | UCL |
|---|---|---|---|
| T24 | LPC Outlet Temperature | 640.0 | 643.0 |
| P30 | HPC Outlet Pressure | 47.2 | 47.85 |
| Nf | Fan Speed | 8980.0 | 9070.0 |
| Nc | Core Speed | 2387.9 | 2388.2 |
| BPR | Bypass Ratio | 8.38 | 8.48 |

---

## ERP API Reference

The mock ERP server exposes three endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/maintenance/ticket` | Create a new maintenance ticket |
| `GET` | `/api/v1/maintenance/tickets` | List all filed tickets |
| `DELETE` | `/api/v1/maintenance/tickets/clear` | Reset the ticket database |

---

## Limitations and Disclaimer

This project is a **proof-of-concept simulation** built for a capstone programme. It is not intended for production aviation use.

- The ML model is trained on a single CMAPSS sub-dataset (FD001) under fixed operational conditions (single flight regime). It has not been evaluated under variable altitude or multi-fault scenarios (FD002–FD004).
- The telemetry source (`telemetry_TF804.csv`) is a synthetic 50-cycle dataset derived from CMAPSS distributions. It represents one simulated engine, not a live fleet data stream.
- The ERP system is a local mock server. Integration with a real ERP (SAP, Oracle, IBM Maximo) would require authentication, schema mapping, and error-handling layers not present here.
- Duplicate suppression relies on a local JSON state file. In a distributed deployment this would need a shared database.

---

## Reproducing the ML Model

The trained model is included as `models/rul_model.pkl`. To retrain from the original NASA CMAPSS dataset:

1. Download the [NASA CMAPSS dataset](https://www.kaggle.com/datasets/behrad3d/nasa-cmaps) from Kaggle.
2. Place `train_FD001.txt` in a `dataset/` directory.
3. Update the `DATASET_PATH` in `train_rul_model.py`.
4. Run:

```bash
python train_rul_model.py
```

This will output validation metrics and overwrite `models/rul_model.pkl`.

---

## License

This project is licensed under the [MIT License](LICENSE).

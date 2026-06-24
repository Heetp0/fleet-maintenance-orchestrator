# ✈️ Fleet Maintenance Orchestrator

**An autonomous multi-agent system for predictive turbofan maintenance and automated AOG ticketing.**
*Built for the Google "Agents for Business" Capstone Project.*

## 📌 Overview

Aircraft on Ground (AOG) events cause massive operational disruptions and financial losses. This project transitions predictive engine maintenance from a manual data science task into an autonomous workflow. 

Using the **Google Agent Development Kit (ADK 2.0)**, this system ingests NASA CMAPSS turbofan telemetry, calculates the Remaining Useful Life (RUL) via a machine learning model, evaluates safety baselines, and autonomously dispatches high-priority maintenance tickets to an Enterprise Resource Planning (ERP) system before catastrophic failure occurs.

## 🧠 Multi-Agent Architecture

The orchestration loop consists of three primary agents:

1. **RUL Analysis Agent:** Ingests CSV telemetry and executes a Random Forest regression tool to predict the engine's RUL.
2. **Guardrail Agent:** Acts as an LLM-as-a-judge to verify predictions against standard operating control limits (e.g., HPC Outlet Pressure, Core Speed) and prevent false positives.
3. **Ticketing Agent:** Queries a local state database to prevent duplicate alerts, then executes a POST request to a mock ERP API to dispatch the maintenance ticket.

## 📂 Project Structure

* `/data/` - Synthetic NASA CMAPSS telemetry and JSON baseline limits.
* `/models/` - Trained Random Forest Regressor (`rul_model.pkl`).
* `/fleet_agents/` - ADK agent definitions and system prompts.
* `/fleet_agents/tools/` - Python tools for RUL calculation and baseline checks.
* `/mock_erp_server/` - FastAPI server exposing the ticketing endpoints.
* `/tests/` - Unit tests and mocked end-to-end integration tests.

## 🚀 Setup & Installation

**1. Clone the repository and install dependencies:**
```bash
git clone https://github.com/Heetp0/fleet-maintenance-orchestrator.git
cd turbofan-rul-orchestrator
pip install -r requirements.txt

```

**2. Configure the API Key:**
Create a `.env` file in the root directory and add your Google Gemini API key:

```text
GEMINI_API_KEY="your_api_key_here"

```

## 💻 Usage Instructions

To run the full multi-agent pipeline, you need two terminal windows.

**Terminal 1: Start the Mock ERP Server**

```bash
python mock_erp_server/server.py

```

**Terminal 2: Run the Orchestrator**
Execute the pipeline against a specific telemetry cycle.

*Run a healthy engine cycle (Nominal):*

```bash
python run_orchestrator.py 10

```

*Run a degrading engine cycle (Alert Triggered):*

```bash
python run_orchestrator.py 38

```

*(Running cycle 38 a second time will demonstrate the agent's state memory preventing a duplicate ticket).*

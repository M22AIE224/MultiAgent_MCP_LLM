# Multi-Agent Orchestration Platform  
**Supervisor → A2A → Agents → MCP Architecture**


---

# ============ Overview  ==============

This project implements a **multi-agent orchestration system** where a central **Supervisor Agent** manages specialized downstream **Agents** (Planning, Data Extract, Visualization, etc.) through **A2A (Agent-to-Agent)** messaging.  
Each agent exposes its capabilities through a dedicated **MCP (Model Control Plane)** service.  

The design supports **distributed execution**, **clean separation of concerns**, and **single-command startup and shutdown**.

---

# =========== Architecture  ============

flowchart 
    S -->[Supervisor Agent] -->|A2A Messaging| A1[Data Agent]
    S -->|A2A Messaging| A2[ML Agent]
    S -->|A2A Messaging| A3[DV Agent]

    A1 -->|MCP API| M1[MCP_DATA]
    A2 -->|MCP API| M2[MCP_ML]
    A3 -->|MCP API| M3[MCP_DV]

#  ============ Flow Summary  ===========

Supervisor Agent receives a task or pipeline command.

It sends A2A JSON-RPC messages to the relevant Agents.

Each Agent performs its function and interacts with its respective MCP backend.

Results are returned up the chain → aggregated by the Supervisor → logged and saved.

#  ============ Components  ============
Supervisor Agent	Central controller that orchestrates all agent workflows via A2A.
Data Agent	Handles data ingestion, cleaning, feature engineering.
ML Agent	Trains ML models, evaluates results, and exports metrics.
DV Agent	Generates visualizations and analytics reports.
MCP Servers	REST interfaces used by each Agent to perform data/model/visualization tasks.
start_all.bat / stop_all.bat	One-click startup and shutdown for all MCPs and agents.


#  ========== Directory Layout  ===========

code/
├── agents/
│   ├── data_agent/         ← implements data agent
│   ├── ml_agent/           ← Implements ml agent
│   ├── dv_agent/           ← Implements dv agents
│
├── supervisor_agent/       ← Implements supervisor
│   ├── agent_main.py  
│   ├── supervisor_agent.py
│
├── mcp_servers/            ← Implements MCP
│   ├── mcp_data.py
│   ├── mcp_ml.py
│   ├── mcp_dv.py
│
├── scripts/
│   ├── start_all.bat       ← Starts all agents + MCPs
│   ├── stop_all.bat        ← Gracefully stops all
│   └── logs/               ← All execution logs
│       ├── data_agent.log
│       ├── ml_agent.log
│       ├── dv_agent.log
│       ├── mcp_*.log
│
├── data/                   ← Source data
│   └── source_data.csv
└── artifacts/              ← Processed results
    ├── data_results/
    ├── ml_results/
    └── dv_results/

# =============================== How to Run ====================================


## Step 1: Environment Setup
# -----------------------------------
pip install -r requirements.txt
# -----------------------------------

## Step 2: LLM Key Setup
# ----------------------------------
update LLM API KEY in /data/apy_key.txt
# ----------------------------------



## Step 3. Start All MCPs and Agents

From the project root:
# -----------------------------------
.\scripts\start_all.bat
# ------------------------------------

This will launch:

All MCP servers (Data / ML / DV)

All Agents (Data / ML / DV)

Logs are streamed to scripts/logs/.

## Step 4. Start Supervisor Agent

Run the Supervisor separately:

# --------------------------------------
python -m supervisor_agent.agent_main
# ---------------------------------------


Once running, the Supervisor will:

Discover available MCPs and Agents

Communicate via A2A

Execute the full pipeline (Data → ML → DV)


## Step 5. Start Flask App for User Input

Run the Student UI Flask App separately:

# --------------------------------------
python .\student_ui\app.py
# ---------------------------------------

## Step 6. Open the browser for Student UI 

Open the browser with URL  http://127.0.0.1:5000
# a Enter the User Query:
Eg - What is the Acedemic Calander
   - Show me the UG Programs and Curriculam
   - Can I see the latest All Curriculam
# b Click on Ask
#c The browser will return the expected results



## Step 7. Stop All Agents and MCP Server once the app use complete
To gracefully stop all background services:

# ------------------------------------
.\scripts\stop_all.bat
# ------------------------------------


This will terminate all python processes spawned by the startup script.

## ========= Example Workflow ==========



Execution chain:

Student URI →
Supervisor → (A2A) → Data Agent → (MCP_DATA)
            → (A2A) → ML Agent   → (MCP_ML)
            → (A2A) → DV Agent   → (MCP_DV)


## ========== Outputs ===================
All data requested by student be stored in below folder

Visualizations → ./student_ui/static/resource
User Response HTML → ./artifacts/User_results/

## ========== Logging and Artifacts ======

# Folder	

scripts/logs/	        # Runtime logs from all components
artifacts/User_results/	# Copy of Student HTML response


## Tech Stack

Python 3.12

LangGraph / LangChain

A2A (Agent-to-Agent) Messaging

MCP (Model Control Plane) APIs

Async IO + HTTPX

Logging + Environment Orchestration via Batch scripts

# ========  Quick Reference ================= 
Command	Purpose
.\scripts\start_all.bat	Starts all agents + MCPs
python -m supervisor_agent.agent_main	Launches Supervisor
.\scripts\stop_all.bat	Stops all services

# ========= Extending the Platform ===========

You can easily add new specialized agents and MCPs:

Add a new folder under agents/ (e.g., forecast_agent/)

Create an mcp_forecast.py under mcp_servers/

Register it in the Supervisor’s discovery routine

Add it to start_all.bat and stop_all.bat

## Author

Prabha Sharma
M22AIE224

Executive Mtech

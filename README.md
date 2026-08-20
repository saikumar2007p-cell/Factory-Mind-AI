# FactoryMind AI — Enterprise Multi-Equipment Prognostics & Industrial Intelligence Platform

```
MONITOR → PREDICT → DIAGNOSE → PRIORITIZE → PLAN → EXECUTE → VERIFY → LEARN → SECURE → RELEASE
```

FactoryMind AI is a production-grade, closed-loop industrial AI platform for real-time fleet health monitoring, remaining useful life (RUL) estimation, Google Gemini grounded root-cause diagnostics, prescriptive maintenance execution, fleet risk planning, and empirical continuous learning across **Turbofans, Industrial Gearboxes, and Spacecraft Solenoid Valves**.

---

## 📁 Repository Structure

The codebase is organized into separated, modular layers:

```
Factory-Mind-AI/
├── backend/                       # 🐍 FastAPI Python Backend Application
│   ├── app/
│   │   ├── main.py                # Application entrypoint, CORS, startup life-cycle
│   │   ├── config.py              # Pydantic Settings & environment manager
│   │   ├── database.py            # Async SQLAlchemy engine (SQLite / Supabase)
│   │   ├── firebase_admin_init.py # Firebase Admin SDK & auth verifier
│   │   ├── models/                # Database entities (Machines, Telemetry, WorkOrders, Alerts)
│   │   ├── routers/               # REST API & WebSocket endpoints (Telemetry, Predictions, RCA)
│   │   ├── services/              # Business logic, Gemini explainer, storage & replay engine
│   │   └── websockets/            # Low-latency live stream broadcaster
│   └── tests/                     # 158 automated pytest test suite (100% PASS)
│
├── frontend/                      # ⚛️ React + Vite Modern Frontend Dashboard
│   ├── src/
│   │   ├── App.jsx                # Main application orchestrator & routing
│   │   ├── components/
│   │   │   ├── Layout/            # TopNavbar (Omnibox Search), Sidebar, Auth Modals
│   │   │   ├── Dashboard/         # Real-time replay gauge, fleet counters, machine switcher
│   │   │   ├── Fleet/             # Fleet Intelligence & risk planning queues
│   │   │   ├── Learning/          # Continuous Learning & executive analytics
│   │   │   ├── Machines/          # Machine directory & detailed telemetry viewer
│   │   │   ├── Alerts/            # Active threshold alarms & acknowledgment ledger
│   │   │   ├── Diagnostics/       # Grounded AI root-cause reasoning
│   │   │   ├── Maintenance/       # Closed-loop prescriptive work orders (Stage 8)
│   │   │   └── Settings/          # Admin-only data connectors, datasets & user management
│   │   └── services/              # Axios API client, SWR in-memory caching & WebSockets
│   ├── package.json
│   └── vite.config.js
│
├── ml/                            # 🧠 Machine Learning Pipelines & Registry
│   ├── dataset_registry.py        # Canonical multi-benchmark dataset catalog
│   ├── adapters/                  # NASA C-MAPSS, PHM 2009 Gearbox, PHMAP 2023 Valve adapters
│   ├── models/                    # LightGBM RUL Regressor & Isolation Forest artifacts
│   └── feature_engineering.py     # 21-channel canonical normalization
│
├── data/                          # 📊 Canonical Datasets
│   ├── raw/
│   │   ├── CMAPSSData/            # NASA C-MAPSS FD001 Turbofan dataset (100 engines)
│   │   ├── phm2009_gearbox/       # PHM 2009 Gearbox benchmark dataset (6 test stands)
│   │   └── phmap2023_valve/       # PHMAP 2023 Valve / Pressure benchmark (5 units)
│   └── reference/                 # Sensor schemas, physics limits, and engineering units
│
├── scripts/                       # 🛠️ Utility & Verification Tooling
│   ├── seed_database.py           # Populates fleet with 111+ units & prognostic baselines
│   ├── generate_canonical_datasets.py # Benchmark CSV dataset generator
│   ├── smoke_test.py              # End-to-end platform verification harness
│   └── verify_multi_unit_diagnostics.py # Multi-unit prediction & RCA verifier
│
├── .env.example                   # Backend environment template
├── .gitignore                     # Git ignore rules (secrets, venv, node_modules)
└── README.md                      # Comprehensive documentation
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (with `pip` and virtual environment support)
- **Node.js 18+** and **npm**

---

### 1. Backend Setup (`FastAPI`)

```bash
# 1. Navigate to the project root
cd Factory-Mind-AI

# 2. Create and activate a Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy configuration template
cp .env.example .env

# 5. Seed the database with 111+ industrial machines (Turbofans, Gearboxes, Valves)
python scripts/seed_database.py

# 6. Start the FastAPI backend server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend REST API and interactive Swagger documentation will be live at:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

### 2. Frontend Setup (`React + Vite`)

```bash
# 1. Open a new terminal and navigate to the frontend directory
cd Factory-Mind-AI/frontend

# 2. Install dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

The frontend application will be live at:
👉 **[http://localhost:3000/](http://localhost:3000/)**

---

## 🧪 Verification & Test Suite

Run the full automated test suite (158 passing tests):

```bash
# Run all backend unit, integration, and security tests
pytest -v

# Run the end-to-end smoke test harness
python scripts/smoke_test.py

# Verify multi-unit predictions and distinct Gemini RCA reports
python scripts/verify_multi_unit_diagnostics.py
```

---

## 🌟 Core Features

### 1. Multi-Equipment Fleet Monitoring
- **NASA C-MAPSS FD001 Turbofan Engines** (Units 1–100): 21 sensor channels (temperatures, pressures, fan speeds, bleed flows).
- **PHM 2009 Industrial Gearboxes** (Units 101–106): High-frequency accelerometer vibration channels, load speeds, and gear teeth wear telemetry.
- **PHMAP 2023 Spacecraft Solenoid Valves** (Units 107–111): Upstream/downstream pressures, transient response timings, and valve command signals.

### 2. Machine Learning Prognostics & Anomaly Detection
- **LightGBM RUL Regressor**: Cycle-by-cycle remaining useful life prediction with piecewise degradation clipping.
- **Isolation Forest**: Multi-dimensional anomaly scoring with hysteresis persistence filtering to eliminate transient false alarms.
- **Composite Health Index**: Deterministic health calculation reflecting physical asset wear.

### 3. Google Gemini Grounded Root-Cause Analysis (RCA)
- Real-time AI diagnostics grounded strictly on verified sensor deltas, z-scores, and operating regimes.
- Automated deterministic fallback ensures instant responses (<1ms) even when external cloud APIs are unreachable.

### 4. Stage 8 Closed-Loop Maintenance Lifecycle
- Strict state-machine transitions: `OPEN` → `ASSIGNED` → `IN_PROGRESS` → `VERIFICATION_REQUIRED` → `VERIFIED`.
- Completed work orders are permanently immutable and auditable.

### 5. Role-Based Access Control (RBAC) & Hardened Security
- **Admin**: Full access to all telemetry, work orders, data connectors, and system settings.
- **Operator**: Operational permissions (assigning, working, and verifying work orders).
- **Viewer**: Read-only monitoring.
- **Settings Access**: Platform settings and configuration views are strictly locked and hidden from non-admin accounts.

### 6. Instant Navigation & Omnibox Recommendation Search
- Stale-While-Revalidate (SWR) in-memory client caching enables instantaneous (<1ms) tab navigation with zero screen flickering.
- Real-time search omnibox with instant recommendations for machines, sensor channels, active alarms, and system views.

---

## 🔒 License
Licensed under the Apache 2.0 License.

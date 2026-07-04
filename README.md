# Eco-Guard

AI-based geospatial monitoring system for Telangana, India — tracks forest cover loss and
shrinking water bodies using satellite NDVI/NDWI analysis (Google Earth Engine, Sentinel-2),
flags concerning changes, and notifies authorities via SMS/email. Includes user accounts and
a personal alert history.

## Architecture
```text
Eco-Guard/
├── backend/
│   ├── app/                              # FastAPI (legacy geofencing & forest monitoring)
│   │   ├── api/
│   │   │   ├── routes.py
│   │   │   └── forest_routes.py
│   │   ├── core/
│   │   ├── db/
│   │   ├── data/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── flask/                            # Flask API (main application)
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── routes.py
│   │       ├── auth.py
│   │       ├── auth_users.py
│   │       ├── verification_log.py
│   │       ├── gee_ndvi.py
│   │       ├── gee_ndwi.py
│   │       ├── alerts_service.py
│   │       ├── db_contacts.py
│   │       ├── regions_data.py
│   │       ├── water_bodies_data.py
│   │       └── config.py
│   │
│   ├── .env
│   ├── .env.example
│   └── venv/
│
├── frontend/
│   ├── react/
│   │   └── src/
│   │       ├── pages/
│   │       │   ├── Home.jsx
│   │       │   ├── Login.jsx
│   │       │   ├── Register.jsx
│   │       │   ├── Tool.jsx
│   │       │   ├── WaterTool.jsx
│   │       │   └── MyAlerts.jsx
│   │       ├── AuthContext.jsx
│   │       └── App.jsx
│   │
│   ├── app.py                            # Optional Streamlit dashboard
│   └── venv/
│
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (running locally)
- Git

## Setup

### 1. PostgreSQL database

```sql
CREATE DATABASE ecoguard;
```

### 2. FastAPI backend (legacy geofencing/danger-zone system)

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend\.env` (see `.env.example`) with at least `DATABASE_URL` and `GEE_ENABLED=false`.

```cmd
python -m app.data.seed_data
uvicorn app.main:app --reload
```
- http://127.0.0.1:8000/health · http://127.0.0.1:8000/docs

### 3. Flask app (main app: forest + water monitoring, auth, alerts)

```cmd
cd backend\flask
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend\flask\.env` (see `.env.example`) with `DATABASE_URL`, `ADMIN_API_TOKEN`, and
`SIMULATE_SMS=true` / `SIMULATE_EMAIL=true` for local testing without real Twilio/SMTP accounts.

```cmd
python run.py
```
- http://127.0.0.1:5000/health

On first run, Flask auto-creates: `telangana_alert_contacts`, `analysis_verifications`,
`users`, `user_sessions`.

### 4. React site

```cmd
cd frontend\react
npm install
```

Create `frontend\react\.env`:
VITE_API_URL=http://127.0.0.1:5000
VITE_ADMIN_TOKEN=dev-admin-token

```cmd
npm run dev
```
- http://127.0.0.1:5173 — landing page, register/login, then Forest Tool / Water Tool / My Alerts

### 5. Streamlit dashboard (optional, talks to FastAPI directly)

```cmd
cd frontend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
- http://localhost:8501

## Running everything together

Four terminals:
1. `backend` → `uvicorn app.main:app --reload` (port 8000)
2. `backend\flask` → `python run.py` (port 5000)
3. `frontend\react` → `npm run dev` (port 5173)
4. (optional) `frontend` → `streamlit run app.py` (port 8501)

## User flow

1. Visit `http://127.0.0.1:5173`, register an account
2. Auto-logged in → redirected to Forest Tool
3. Pick a region, set a date range (max 3 days), Run analysis
4. Review results (NDVI/NDWI change, loss %, before/after imagery, map)
5. Mark **Legal** or **Illegal** — illegal triggers SMS/email alerts to region contacts
6. Every decision is recorded in `analysis_verifications` (who, when, what)
7. **My Alerts** page shows your own decision history
8. Switch to **Water Tool** for the same flow on Telangana lakes/reservoirs

## Notes

- Google Earth Engine is disabled by default (`GEE_ENABLED=false`); analysis falls back to
  deterministic simulation so the app is fully testable without a GEE account. See the GEE setup
  section below to enable real satellite data.
- SMS/email alerts default to simulation mode (logged to console).
- Never commit `.env` files or GEE service-account key JSON files — see `.gitignore`.

## Enabling real Google Earth Engine (optional)

1. Register at https://code.earthengine.google.com/register (free for academic/noncommercial use)
2. Create a Google Cloud service account with **Earth Engine Resource Viewer**, **Earth Engine
   Resource Writer**, and **Service Usage Consumer** roles
3. Download its JSON key, save it locally (never commit it)
4. In both `backend\.env` and `backend\flask\.env`:
GEE_ENABLED=true
GEE_PROJECT=<your-gcp-project-id>
GEE_CREDENTIALS_JSON=<absolute path to the key file>
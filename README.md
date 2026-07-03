# Eco-Guard

AI-based geospatial forest monitoring and alert system for Telangana, India.
Detects vegetation/forest loss from satellite NDVI data (Google Earth Engine,
Sentinel-2), flags danger zones, and notifies authorities via SMS/email.

## Architecture

Three independent services, each with its own virtual environment:
```text
Eco-Guard/
├── backend/                          # FastAPI — Core API, danger zones, forest change tracking
│   ├── app/
│   │   ├── api/                      # API routes
│   │   │   ├── routes.py             # Danger zone endpoints
│   │   │   └── forest_routes.py      # Forest monitoring endpoints
│   │   ├── core/
│   │   │   └── config.py             # Application settings
│   │   ├── db/                       # SQLAlchemy engine & session
│   │   ├── models/
│   │   │   ├── forest.py
│   │   │   ├── danger_zone.py
│   │   │   └── event.py
│   │   ├── services/                 # Business logic
│   │   │   ├── GEE client
│   │   │   ├── Geofencing
│   │   │   ├── Alerts
│   │   │   └── Background worker
│   │   └── main.py                   # FastAPI entry point
│   │
│   ├── flask/                        # Flask microservice (Sentinel-2 NDVI Analysis)
│   │   └── app/
│   │
│   ├── .env                          # FastAPI configuration
│   │                                 # (DATABASE_URL, GEE, Twilio, etc.)
│   └── venv/
│
├── frontend/
│   ├── react/                        # React + Vite Admin Dashboard (Port 5173)
│   ├── app.py                        # Streamlit Dashboard (Port 8501)
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

### 1. FastAPI backend

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend\.env` with at least:
DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/ecoguard
GEE_ENABLED=false

Create the database:
```sql
CREATE DATABASE ecoguard;
```

Seed reference data:
```cmd
python -m app.data.seed_data
```

Run:
```cmd
uvicorn app.main:app --reload
```
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

### 2. Flask NDVI microservice

```cmd
cd backend\flask
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend\flask\.env` with at least `DATABASE_URL` (same as above), `ADMIN_API_TOKEN`, and `SIMULATE_SMS=true` / `SIMULATE_EMAIL=true` for local testing without real Twilio/SMTP.

Run:
```cmd
python run.py
```
- http://127.0.0.1:5000/health

### 3. React dashboard

```cmd
cd frontend\react
npm install
```

Create `frontend\react\.env`:
VITE_API_URL=http://127.0.0.1:5000
VITE_ADMIN_TOKEN=dev-admin-token

Run:
```cmd
npm run dev
```
- http://127.0.0.1:5173

### 4. Streamlit dashboard (optional, talks to FastAPI)

```cmd
cd frontend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
- http://localhost:8501

## Running everything together

Open 3–4 terminals:
1. `backend` → `uvicorn app.main:app --reload`
2. `backend\flask` → `python run.py`
3. `frontend\react` → `npm run dev`
4. (optional) `frontend` → `streamlit run app.py`

## Notes

- Google Earth Engine is disabled by default (`GEE_ENABLED=false`); NDVI analysis falls back to deterministic simulation so the app is fully testable without a GEE account.
- SMS/email alerts default to simulation mode (logged to console, not actually sent).
- Never commit `.env` files — see `.gitignore`.
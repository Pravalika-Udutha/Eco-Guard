# Eco-Guard API Testing Guide

## Quick Start

- FastAPI docs: http://127.0.0.1:8000/docs
- Flask health: http://127.0.0.1:5000/health
- React dashboard: http://127.0.0.1:5173
- Streamlit dashboard: http://localhost:8501

## FastAPI: Forest Monitoring Test Scenarios

### 1. List all Telangana forest regions
```bash
curl -X GET "http://127.0.0.1:8000/forest/regions"
```

### 2. Find region for a location
```bash
curl -X GET "http://127.0.0.1:8000/forest/regions/location/17.5/78.5"
```

### 3. Get seasonal NDVI thresholds
```bash
curl -X GET "http://127.0.0.1:8000/forest/thresholds"
```

### 4. Report a detected forest change
```bash
curl -X POST "http://127.0.0.1:8000/forest/changes" ^
  -H "Content-Type: application/json" ^
  -d "{\"region_id\": 1, \"latitude\": 17.51, \"longitude\": 78.51, \"ndvi_before\": 0.65, \"ndvi_after\": 0.35, \"area_affected_sq_meters\": 50000, \"change_date\": \"2024-04-03T10:00:00Z\", \"detection_confidence\": 0.85, \"satellite_source\": \"Sentinel-2\"}"
```
*(Windows `cmd` needs `^` for line continuation and escaped `"` inside `-d`; adjust for PowerShell/Bash if needed.)*

### 5. Get pending changes for verification
```bash
curl -X GET "http://127.0.0.1:8000/forest/changes/pending"
```

### 6. Admin verification — mark ILLEGAL (triggers alerts)
```bash
curl -X POST "http://127.0.0.1:8000/forest/verify" ^
  -H "Content-Type: application/json" ^
  -d "{\"change_id\": 1, \"admin_id\": \"admin_001\", \"admin_name\": \"Test Admin\", \"is_legal\": false, \"change_type\": \"illegal_logging\", \"verification_notes\": \"Clear evidence of unauthorized tree cutting.\", \"alert_channels\": \"SMS,Email\"}"
```

### 7. Or mark LEGAL (no alerts sent)
```bash
curl -X POST "http://127.0.0.1:8000/forest/verify" ^
  -H "Content-Type: application/json" ^
  -d "{\"change_id\": 2, \"admin_id\": \"admin_001\", \"is_legal\": true, \"change_type\": \"approved_clearing\", \"verification_notes\": \"Government-approved.\"}"
```

### 8. List alert recipients for a region
```bash
curl -X GET "http://127.0.0.1:8000/forest/recipients/1"
```

### 9. Add a new alert recipient
```bash
curl -X POST "http://127.0.0.1:8000/forest/recipients" ^
  -H "Content-Type: application/json" ^
  -d "{\"region_id\": 1, \"name\": \"District Collector\", \"organization\": \"District Administration\", \"role\": \"Government Officer\", \"phone\": \"+91-40-23999999\", \"email\": \"dc@example.gov.in\"}"
```

## FastAPI: Danger Zone / Geofencing Test Scenarios

### List danger zones
```bash
curl -X GET "http://127.0.0.1:8000/danger-zones"
```

### Simulate a location update (geofencing + alert check)
```bash
curl -X POST "http://127.0.0.1:8000/update-location" ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 8.0, \"longitude\": 80.0, \"user_id\": \"tester\"}"
```

## Flask: NDVI Analysis Test Scenarios

All Flask admin routes require `X-Admin-Token` matching `ADMIN_API_TOKEN` in `backend/flask/.env`.

### List regions
```bash
curl "http://127.0.0.1:5000/regions" -H "X-Admin-Token: dev-admin-token"
```

### Run NDVI analysis for a region
```bash
curl "http://127.0.0.1:5000/analyze/hyderabad?period1_start=2024-01-01&period1_end=2024-01-03" -H "X-Admin-Token: dev-admin-token"
```
*(Note the `analysis_id` in the response — you'll need it for verify.)*

### Verify as illegal (triggers SMS/email alert dispatch)
```bash
curl -X POST "http://127.0.0.1:5000/verify" ^
  -H "Content-Type: application/json" ^
  -H "X-Admin-Token: dev-admin-token" ^
  -d "{\"analysis_id\": \"YOUR_ANALYSIS_ID\", \"decision\": \"illegal\"}"
```

## Data Flow
Satellite Data (GEE / simulated)
-> Detect Forest Change (NDVI Drop)
-> Save to ForestChange / analysis store (pending)
-> Admin Reviews (React or Streamlit dashboard)
-> Admin Verifies (Legal / Illegal)
-> If ILLEGAL: fetch recipients, send alerts (SMS, Email)
-> If LEGAL: log & archive, no alerts

## Troubleshooting

**"Region not found" when querying location**
- Check coordinates fall within a region's GeoJSON polygon.
- Use `/docs` (FastAPI) to inspect region boundaries.

**No recipients returned for a region**
- Ensure recipients exist for that `region_id` and `is_active = true`.

**No SMS received after marking illegal**
- Check `SIMULATE_SMS` in `backend/flask/.env` — if `true`, alerts are only logged to console, not actually sent.
- See the "Personal alert number" section in the README for real SMS setup.
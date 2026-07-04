# Eco-Guard Testing Guide

## Quick Start

- FastAPI docs: http://127.0.0.1:8000/docs
- Flask health: http://127.0.0.1:5000/health
- React site: http://127.0.0.1:5173

## User Flow (via browser — recommended)

1. Go to http://127.0.0.1:5173 → **Register** → creates an account, auto-logs in
2. You're redirected to the **Forest Tool** — pick a region, set dates (max 3 days), **Run analysis**
3. Review the results page, click **Legal** or **Illegal**
4. Illegal triggers alerts (SMS/email — simulated by default) to that region's contacts
5. Click **My Alerts** in the top bar — see your own decision history
6. Click **Water Tool** — same flow for lakes/reservoirs (Hussain Sagar, Osman Sagar, etc.)

## Flask API — manual testing (curl)

All `/auth/*` routes are public. Everything else under the user-facing tool requires a
**Bearer token** from login. Admin-only oversight routes (`/verifications`, `/contacts/<region>`)
use the separate static `X-Admin-Token` header instead.

### 1. Register a user
```bash
curl -X POST "http://127.0.0.1:5000/auth/register" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"testuser\", \"password\": \"testpass123\"}"
```

### 2. Log in (grab the token from the response)
```bash
curl -X POST "http://127.0.0.1:5000/auth/login" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"testuser\", \"password\": \"testpass123\"}"
```
Response includes `"token": "..."` — use it as `Authorization: Bearer <token>` below.

### 3. Confirm the session
```bash
curl "http://127.0.0.1:5000/auth/me" -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Forest: list regions
```bash
curl "http://127.0.0.1:5000/regions" -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Forest: run NDVI analysis
```bash
curl "http://127.0.0.1:5000/analyze/hyderabad?period1_start=2024-01-01&period1_end=2024-01-03" -H "Authorization: Bearer YOUR_TOKEN"
```
Note the `analysis_id` in the response.

### 6. Forest: verify as illegal (triggers alerts)
```bash
curl -X POST "http://127.0.0.1:5000/verify" ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -d "{\"analysis_id\": \"YOUR_ANALYSIS_ID\", \"decision\": \"illegal\"}"
```

### 7. Water: list water bodies
```bash
curl "http://127.0.0.1:5000/water-bodies" -H "Authorization: Bearer YOUR_TOKEN"
```

### 8. Water: run NDWI analysis
```bash
curl "http://127.0.0.1:5000/analyze-water/hussain-sagar?period1_start=2024-01-01&period1_end=2024-01-03" -H "Authorization: Bearer YOUR_TOKEN"
```

### 9. Water: verify as illegal
```bash
curl -X POST "http://127.0.0.1:5000/verify-water" ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -d "{\"analysis_id\": \"YOUR_ANALYSIS_ID\", \"decision\": \"illegal\"}"
```

### 10. Your own alert history
```bash
curl "http://127.0.0.1:5000/my-alerts" -H "Authorization: Bearer YOUR_TOKEN"
```

### 11. Admin oversight (static token, not user login)
```bash
curl "http://127.0.0.1:5000/verifications" -H "X-Admin-Token: dev-admin-token"
curl "http://127.0.0.1:5000/contacts/hyderabad" -H "X-Admin-Token: dev-admin-token"
```

## Data Flow
Satellite Data (GEE / simulated) — NDVI (forest) or NDWI (water)
-> /analyze/<region> or /analyze-water/<slug>
-> User reviews on Results page (React)
-> POST /verify or /verify-water (legal | illegal)
-> Logged to analysis_verifications (who, when, domain, decision)
-> If ILLEGAL: alerts dispatched (SMS via Twilio, Email via SMTP/SendGrid)
-> User's own decisions visible at GET /my-alerts

## Troubleshooting

**401 Unauthorized on tool endpoints** — token missing/expired; log in again via `/auth/login`
and use the fresh token (sessions last 14 days).

**"Region not found" / "Water body not found"** — check the slug matches exactly
(`regions_data.py` / `water_bodies_data.py`), lowercase, hyphenated.

**No SMS received after marking illegal** — check `SIMULATE_SMS` in `backend\flask\.env`; if
`true`, alerts are only logged to console. See README's Twilio setup notes.

**GEE errors in Flask console** — if `GEE_ENABLED=true`, common issues are missing IAM roles
(`Service Usage Consumer`, `Earth Engine Resource Writer`) — see README's GEE section. With
`GEE_ENABLED=false`, analysis always uses deterministic simulation and these errors won't occur.
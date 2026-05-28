# Mock Maritime Web App

A lightweight Flask application simulating a maritime fleet management system.
Run this **before** starting the AI agent pipeline so Playwright scripts have a live target.

## Start the app

```bash
cd mock_app
pip install flask
python app.py
```

App runs at: http://localhost:5000

## Pages

| URL | Feature |
|-----|---------|
| / | Fleet Dashboard |
| /crew-certs | Crew Certification Management |
| /fatigue | Fatigue & Rest Hours Tracking |
| /port-call | Port Call Management |
| /incidents | Incident & Near-Miss Reporting |
| /voyage | Voyage Planning |

## API endpoints (used by Playwright mocking)

- `GET /api/crew` — crew certification data
- `GET /api/fatigue` — rest hours data
- `GET /api/incidents` — incident register
- `GET /api/voyages` — voyage register

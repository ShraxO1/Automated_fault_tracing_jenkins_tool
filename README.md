# Automated Fault Tracing Prototype

Minimal runnable prototype aligned with mid-semester report.

## Features (Current)
- Simulated Jenkins build ingestion (JSON fixtures)
- Log normalization (timestamp + level extraction, noise filtering)
- Failure taxonomy (YAML configurable)
- Rule-based classifier (regex patterns with confidence scoring)
- Optional ML baseline (TF-IDF + linear classifier) – now disabled by default
- Summarization (extract exception, failing test ids, suspected commit)
- Commit attribution heuristic
- FastAPI service exposing endpoints
- Features status endpoint (`/features`) summarizing active vs deferred modules

## Quick Start (Rules-Only Lightweight)
```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python main.py  # http://127.0.0.1:8000
```
This mode has NO heavy ML deps (scikit-learn, numpy, pandas, nltk). Ingestion uses only deterministic rules.

## (Optional) Enable ML Classifier
```
pip install -r requirements.txt
pip install -r requirements-ml.txt
$env:ENABLE_ML=1   # PowerShell (Linux/macOS: export ENABLE_ML=1)
python main.py
```
Then you can call POST /train with samples. If ENABLE_ML is not set, /train returns a deferred status.

## Endpoints
- POST /ingest  {"build_id":"B123","log":"..."}
- GET /build/{build_id}
- GET /taxonomy
- GET /features  (active vs deferred modules)
- POST /train (only active when ENABLE_ML=1)

## Deferred (Next Iteration)
- ML/NLP classification as default path (currently optional only)
- Clustering (HDBSCAN) and novel pattern surfacing
- Persistence (SQLite/Postgres) replacing in-memory store
- Risk scoring & early failure prediction

## Example Train Payload
```
[
  {"text": "AssertionError: expected 2 got 3", "label": "Test:Failure:Assertion"},
  {"text": "Read timed out while connecting", "label": "Infra:Network:Timeout"}
]
```

## Design Notes
- Optional ML keeps core footprint small and faster to set up.
- Setting ENABLE_ML later is fine; historical records remain.

## Next Steps
Add persistence, clustering (HDBSCAN), risk scoring, dashboard UI.

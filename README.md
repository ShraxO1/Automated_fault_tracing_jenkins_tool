# Automated Fault Tracing

Minimal runnable prototype focused on rapid feedback for failing CI builds (Jenkins-style logs). Core philosophy: start with deterministic, explainable steps (normalization + rules) and layer optional ML without forcing heavyweight dependencies.

## Features

- **Build Ingestion**: Accepts build log + optional metadata + commit list; stores in in-memory store
- **Log Normalization**: Cleans and tokenizes raw text into structured events while filtering noise & ANSI escape codes
- **Failure Taxonomy**: YAML-driven list of hierarchical failure codes + indicator strings feeding rule engine
- **Rule-Based Classification**: Deterministic regex indicator weighting to assign best failure code with normalized confidence
- **Optional ML Baseline**: TF-IDF + Logistic Regression (scikit-learn) for fallback/augmentation when rules have low confidence (opt-in via `ENABLE_ML`)
- **Summarization**: Extracts exceptions, assertion detail, and test identifiers; produces compact human summary string
- **Commit Attribution Heuristic**: Scores provided recent commits against stack frames, test names, and keyword hints to suggest likely culprit commit
- **FastAPI Service**: JSON API to ingest and retrieve build analyses, taxonomy, feature status, and training
- **Markdown/PDF Reporting**: On-demand build report rendering (`/build/{id}/report.md` / `.pdf` when Pandoc available)
- **Feature Status Endpoint**: `/features` enumerates active, available, or deferred modules for transparency

## Quick Start (Rules-Only / Lightweight)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The server will start at http://127.0.0.1:8000

## (Optional) Enable ML Classifier

```bash
pip install -r requirements-ml.txt
export ENABLE_ML=1  # On Windows: set ENABLE_ML=1
python main.py
```

Then supply training data:
```bash
curl -X POST http://127.0.0.1:8000/train \
  -H "Content-Type: application/json" \
  -d '[
    {"text": "AssertionError: expected 2 got 3", "label": "Test:Failure:Assertion"},
    {"text": "Read timed out while connecting", "label": "Infra:Network:Timeout"}
  ]'
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /ingest | Ingest & analyze a build log; returns label, confidence, summary, attribution |
| GET | /build/{build_id} | Full stored record (raw log, events, label, scores, summary, attribution) |
| GET | /build/{build_id}/report.md | Markdown report rendering |
| GET | /build/{build_id}/report.pdf | PDF report via Pandoc (501 if unavailable) |
| GET | /taxonomy | Raw YAML taxonomy content |
| GET | /features | Feature lifecycle states |
| POST | /train | Train ML classifier (active only if `ENABLE_ML=1`) |
| GET | /health | Basic liveness check |

## Example Usage

### Ingest a Build Log

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "B5001",
    "log": "2025-09-07 10:00:00 ERROR AssertionError: expected 2 got 3 in test_authentication\n2025-09-07 10:00:12 ERROR Test failed: test_authentication",
    "metadata": {"job_name": "unit-tests"},
    "commits": [
      {
        "sha": "abc1234",
        "author": "jdoe", 
        "message": "Fix authentication timeout handling",
        "changed_files": ["src/auth/login.py", "tests/test_authentication.py"]
      }
    ]
  }'
```

### Get Build Analysis

```bash
curl http://127.0.0.1:8000/build/B5001
```

### Get Markdown Report

```bash
curl http://127.0.0.1:8000/build/B5001/report.md
```

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| ENABLE_ML | Enable optional ML pipeline & `/train` | 0 (disabled) |

## Directory Structure

```
automated-fault-tracing/
├── attribution/
│   ├── __init__.py
│   └── commit_attributor.py
├── classification/
│   ├── __init__.py
│   ├── ml_model.py
│   └── rules.py
├── models/
│   ├── __init__.py
│   └── pydantic_models.py
├── normalization/
│   ├── __init__.py
│   └── normalizer.py
├── reporting/
│   ├── __init__.py
│   └── reporter.py
├── summarization/
│   ├── __init__.py
│   └── summarizer.py
├── main.py
├── requirements-ml.txt
├── requirements.txt
├── taxonomy.yaml
└── README.md
```

## Characteristics

- **Minimal dependencies**: Fast cold start
- **Consistent deterministic classification**: Rules-first approach
- **Optional ML augmentation**: No forced heavyweight dependencies
- **Explainable results**: Clear scoring and confidence metrics
- **Extensible taxonomy**: Easy to add new failure patterns via YAML

## License

MIT License

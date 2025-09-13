# Automated Fault Tracing

Minimal runnable prototype focused on rapid feedback for failing CI builds (Jenkins‑style logs). Core philosophy: start with deterministic, explainable steps (normalization + rules) and layer optional ML without forcing heavyweight dependencies.

---
## Feature Overview (High-Level)
- **Build Ingestion**: Accepts build log + optional metadata + commit list; stores in in‑memory store.
- **Log Normalization**: Cleans and tokenizes raw text into structured events (timestamp, level, text) while filtering noise & ANSI escape codes.
- **Failure Taxonomy**: YAML-driven list of hierarchical failure codes + indicator strings feeding rule engine.
- **Rule-Based Classification**: Deterministic regex indicator weighting to assign best failure code with a normalized confidence.
- **Optional ML Baseline**: TF‑IDF + Logistic Regression (scikit-learn) for fallback / augmentation when rules have low confidence (opt‑in via `ENABLE_ML`).
- **Summarization**: Extracts exceptions, assertion detail, and test identifiers; produces a compact human summary string.
- **Commit Attribution Heuristic**: Scores provided recent commits against stack frames, test names, and keyword hints to suggest a likely culprit commit.
- **FastAPI Service**: JSON API to ingest and retrieve build analyses, taxonomy, feature status, and training.
- **Markdown/PDF Reporting**: On-demand build report rendering (`/build/{id}/report.md` / `.pdf` when Pandoc available).
- **Feature Status Endpoint**: `/features` enumerates active, available, or deferred modules for transparency.

---
## Detailed Feature Descriptions

### 1. Build Ingestion
Endpoint: `POST /ingest`
Input JSON (`BuildPayload`):
```
{
  "build_id": "B5001",
  "log": "2025-09-07 10:00:00 ERROR ...",
  "metadata": {"job_name": "unit-tests"},
  "commits": [
    {"sha": "abc1234", "author": "jdoe", "message": "Fix timeout handling", "changed_files": ["src/net/retry.py", "tests/test_retry.py"]}
  ]
}
```
Processing Steps:
1. Store raw payload in in‑memory dictionary keyed by `build_id`.
2. Normalize log into structured events.
3. Classify using rule engine (optionally augmented by ML if enabled & higher confidence).
4. Summarize (exceptions, tests, assertion snippet).
5. Attribute commit if commit metadata supplied.
6. Persist enriched record back to store.

### 2. Log Normalization (`normalization/normalizer.py`)
Transforms raw multiline text into an ordered list of events:
- Strips ANSI escape codes & leading noise prefixes (`[Pipeline]`, color codes, download chatter).
- Extracts timestamp (`YYYY-MM-DD HH:MM:SS`) and level tokens (INFO, WARN, ERROR, etc.).
- Preserves line index for later correlation / heuristic weighting.
Result Shape:
```
[{"index": 42, "timestamp": "2025-09-07 10:00:00", "level": "ERROR", "text": "AssertionError: expected 2 got 3"}, ...]
```

### 3. Failure Taxonomy (`taxonomy.yaml`)
Defines structured failure categories (e.g. `Test:Failure:Assertion`, `Infra:Network:Timeout`). Each code lists indicator substrings which seed rule patterns. Editing this file automatically adjusts classification without code changes.

### 4. Rule-Based Classification (`classification/rules.py`)
Mechanics:
- For each taxonomy indicator an escaped regex is created with weight=2.
- Adds generic fallback patterns (e.g. `exception`).
- Iterates over normalized events; if a rule matches a line, increments that code's score by weight.
- Chooses max score; confidence = score_of_best / sum(all_scores). Empty score set → `UNCLASSIFIED` with 0.0 confidence.
Why Rules First:
- Deterministic, explainable, fast (< ms for typical logs).
- Easy to extend via taxonomy file.

### 5. Optional ML Baseline (`classification/ml_model.py`)
Design:
- Lazy degradation: if ML deps absent, module still imports and classifier reports unavailable state (no crash or conditional imports needed elsewhere).
- Pipeline: Raw concatenated recent log window → TF‑IDF (1–2 grams, max 5k features) → Logistic Regression.
Activation:
1. Install `requirements-ml.txt`.
2. Set env var `ENABLE_ML=1`.
3. Call `POST /train` with labeled samples.
Fallback Logic in `/ingest`:
- If rule confidence < 0.55 and ML is trained, prefer higher-confidence ML prediction; embed both rule scores and ML distribution for transparency.

### 6. Summarization (`summarization/summarizer.py`)
Extracts signals from last ~300 log lines:
- Exception class names (first 3 unique).
- Assertion message (first occurrence trimmed to 180 chars).
- Up to 5 distinct test function identifiers (`test_...`).
Outputs structured summary plus a human readable pipe-delimited sentence.

### 7. Commit Attribution (`attribution/commit_attributor.py`)
Heuristic scoring over supplied commit list:
- Matches changed filenames against stack frames & occurrence in text (score +3 each hit).
- Boosts if related test name stem appears in changed file (+2).
- Adds slight bonus for network timeout semantic hint (+1) if relevant keywords align.
Returns top scoring commit if score > 0 else `null`.

### 8. Reporting (`/build/{id}/report.md|pdf`)
Generates Markdown summarizing label, confidence, suspected commit, scores, and a tail of recent log lines (120). PDF generation requires `pandoc` on PATH; otherwise 501 returned.

### 9. Feature Status (`/features`)
Provides a machine-readable inventory of module lifecycle states (active / available / deferred / planned) aiding UI gating & docs automation.

---
## Architecture Snapshot
```
            +--------------+
Client ---> |  /ingest     | --+--> Normalize --> Classify (Rules [+ML?]) --+--> Summarize
            +--------------+   |                                            |
                                |                                            +--> Commit Attribution
                                |
                                +--> In-Memory Store (build record JSON)

Retrieval: /build/{id}  /build/{id}/report.*  /taxonomy  /features  /train
```
Data Flow (simplified): Raw Log → Events → (Scores, Label) → Summary → Attribution → Persisted Record.

---
## API Endpoint Reference
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

---
## Quick Start (Rules-Only / Lightweight)
```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python main.py  # http://127.0.0.1:8000
```
Characteristics:
- Minimal dependencies; fast cold start.
- `/train` returns deferred status.
- Consistent deterministic classification.

## (Optional) Enable ML Classifier
```
pip install -r requirements.txt
pip install -r requirements-ml.txt
$env:ENABLE_ML=1   # PowerShell (Linux/macOS: export ENABLE_ML=1)
python main.py
```
Then supply training data:
```
POST /train
[
  {"text": "AssertionError: expected 2 got 3", "label": "Test:Failure:Assertion"},
  {"text": "Read timed out while connecting", "label": "Infra:Network:Timeout"}
]
```
Verification: call `/features` → `ml_classification` should switch from `available` to `active` after training.

---
## Configuration & Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| ENABLE_ML | Enable optional ML pipeline & `/train` | 0 (disabled) |
| PORT (future) | (Planned) override server port | 8000 |

Other runtime toggles (planned): persistence backend DSN, clustering enable flag.

---
## Data Structures (Key Shapes)
Build Record (stored):
```
{
  "raw_log": "...",
  "metadata": {"job_name": "unit-tests"},
  "commits": [{"sha":"abc1234","author":"jdoe","message":"Fix...","changed_files":["src/net/retry.py"]}],
  "events": [...],
  "label": "Test:Failure:Assertion",
  "confidence": 0.87,
  "scores": {"Test:Failure:Assertion": 14, "Infra:Network:Timeout": 2},
  "summary": {"label":"...","confidence":0.87,"exceptions":[...],"tests":[...],"summary":"Label: ..."},
  "attribution": {"sha":"abc1234","author":"jdoe","score":7,"changed_files":[...],"tests_detected":[...]},
  "ingested_at": 1694000000.123
}
```

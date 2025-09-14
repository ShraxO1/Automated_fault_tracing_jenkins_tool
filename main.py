"""
Automated Fault Tracing - Main FastAPI Application
Minimal runnable prototype for rapid CI build failure analysis
"""

import os
import time
import subprocess
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
import uvicorn
import yaml

from models.pydantic_models import (
    BuildPayload, BuildRecord, FeatureStatus, TrainingData, 
    NormalizedEvent, ClassificationResult, SummaryResult, AttributionResult
)
from normalization.normalizer import LogNormalizer
from classification.rules import RuleClassifier
from classification.ml_model import MLClassifier
from summarization.summarizer import LogSummarizer
from attribution.commit_attributor import CommitAttributor
from reporting.reporter import ReportGenerator

# Initialize FastAPI app
app = FastAPI(
    title="Automated Fault Tracing",
    description="Rapid feedback system for failing CI builds",
    version="1.0.0"
)

# In-memory storage for build records
build_store: Dict[str, BuildRecord] = {}

# Initialize components
normalizer = LogNormalizer()
rule_classifier = RuleClassifier()
ml_classifier = MLClassifier()
summarizer = LogSummarizer()
attributor = CommitAttributor()
reporter = ReportGenerator()

# Check if ML is enabled
ML_ENABLED = os.getenv("ENABLE_ML", "0") == "1"

@app.post("/ingest", response_model=Dict[str, Any])
async def ingest_build(payload: BuildPayload):
    """
    Ingest and analyze a build log
    """
    build_id = payload.build_id

    # Normalize log
    events = normalizer.normalize(payload.log)

    # Classify using rules
    rule_result = rule_classifier.classify(events)

    # Use ML if enabled and rule confidence is low
    final_classification = rule_result
    if ML_ENABLED and rule_result.confidence < 0.55 and ml_classifier.is_trained():
        ml_result = ml_classifier.classify(payload.log)
        if ml_result.confidence > rule_result.confidence:
            final_classification = ml_result

    # Summarize
    summary = summarizer.summarize(events)

    # Attribute commits
    attribution = None
    if payload.commits:
        attribution = attributor.attribute(events, payload.commits)

    # Create build record
    build_record = BuildRecord(
        build_id=build_id,
        raw_log=payload.log,
        metadata=payload.metadata or {},
        commits=payload.commits or [],
        events=events,
        label=final_classification.label,
        confidence=final_classification.confidence,
        scores=final_classification.scores,
        summary=summary.dict(),
        attribution=attribution.dict() if attribution else None,
        ingested_at=time.time()
    )

    # Store record
    build_store[build_id] = build_record

    return {
        "build_id": build_id,
        "label": final_classification.label,
        "confidence": final_classification.confidence,
        "summary": summary.summary,
        "attribution": attribution.dict() if attribution else None,
        "status": "success"
    }

@app.get("/build/{build_id}", response_model=BuildRecord)
async def get_build(build_id: str):
    """
    Retrieve full build record
    """
    if build_id not in build_store:
        raise HTTPException(status_code=404, detail="Build not found")

    return build_store[build_id]

@app.get("/build/{build_id}/report.md", response_class=PlainTextResponse)
async def get_markdown_report(build_id: str):
    """
    Generate markdown report for build
    """
    if build_id not in build_store:
        raise HTTPException(status_code=404, detail="Build not found")

    build_record = build_store[build_id]
    report = reporter.generate_markdown_report(build_record)

    return Response(content=report, media_type="text/markdown")

@app.get("/build/{build_id}/report.pdf")
async def get_pdf_report(build_id: str):
    """
    Generate PDF report for build (requires pandoc)
    """
    # Check if pandoc is available
    try:
        subprocess.run(["pandoc", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise HTTPException(status_code=501, detail="PDF generation not available - pandoc not found")

    if build_id not in build_store:
        raise HTTPException(status_code=404, detail="Build not found")

    build_record = build_store[build_id]
    pdf_content = reporter.generate_pdf_report(build_record)

    return Response(content=pdf_content, media_type="application/pdf")

@app.get("/taxonomy", response_class=PlainTextResponse)
async def get_taxonomy():
    """
    Return raw YAML taxonomy content
    """
    try:
        with open("taxonomy.yaml", "r") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Taxonomy file not found")

@app.get("/features", response_model=Dict[str, str])
async def get_features():
    """
    Return feature status
    """
    features = {
        "log_normalization": "active",
        "rule_classification": "active", 
        "summarization": "active",
        "commit_attribution": "active",
        "reporting": "active"
    }

    if ML_ENABLED:
        if ml_classifier.is_trained():
            features["ml_classification"] = "active"
        else:
            features["ml_classification"] = "available"
    else:
        features["ml_classification"] = "deferred"

    return features

@app.post("/train")
async def train_ml_model(training_data: List[TrainingData]):
    """
    Train ML classifier (if enabled)
    """
    if not ML_ENABLED:
        return {"status": "deferred", "message": "ML features not enabled"}

    try:
        ml_classifier.train(training_data)
        return {"status": "success", "message": f"Model trained with {len(training_data)} samples"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Basic health check
    """
    return {
        "status": "healthy",
        "builds_stored": len(build_store),
        "ml_enabled": ML_ENABLED,
        "timestamp": time.time()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

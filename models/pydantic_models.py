"""
Pydantic data models for Automated Fault Tracing
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class CommitInfo(BaseModel):
    """Information about a commit"""
    sha: str
    author: str
    message: str
    changed_files: List[str]

class BuildPayload(BaseModel):
    """Input payload for build ingestion"""
    build_id: str
    log: str
    metadata: Optional[Dict[str, Any]] = None
    commits: Optional[List[CommitInfo]] = None

class NormalizedEvent(BaseModel):
    """Normalized log event"""
    index: int
    timestamp: Optional[str] = None
    level: Optional[str] = None
    text: str

class ClassificationResult(BaseModel):
    """Result of classification"""
    label: str
    confidence: float
    scores: Dict[str, int]

class SummaryResult(BaseModel):
    """Summary of log analysis"""
    label: str
    confidence: float
    exceptions: List[str]
    tests: List[str]
    assertion: Optional[str] = None
    summary: str

class AttributionResult(BaseModel):
    """Result of commit attribution"""
    sha: Optional[str] = None
    author: Optional[str] = None
    score: int = 0
    changed_files: List[str] = []
    tests_detected: List[str] = []

class BuildRecord(BaseModel):
    """Complete build record stored in memory"""
    build_id: str
    raw_log: str
    metadata: Dict[str, Any]
    commits: List[CommitInfo]
    events: List[NormalizedEvent]
    label: str
    confidence: float
    scores: Dict[str, int]
    summary: Dict[str, Any]
    attribution: Optional[Dict[str, Any]] = None
    ingested_at: float

class FeatureStatus(BaseModel):
    """Status of system features"""
    feature_name: str
    status: str  # active, available, deferred, planned

class TrainingData(BaseModel):
    """Training data for ML classifier"""
    text: str
    label: str

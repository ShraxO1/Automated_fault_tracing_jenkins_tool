"""
Rule-based classification engine
Uses taxonomy-driven regex patterns for deterministic failure classification
"""

import re
import yaml
from typing import List, Dict
from models.pydantic_models import NormalizedEvent, ClassificationResult

class RuleClassifier:
    """Rule-based failure classifier using taxonomy patterns"""

    def __init__(self, taxonomy_file: str = "taxonomy.yaml"):
        self.taxonomy_file = taxonomy_file
        self.rules = {}
        self._load_taxonomy()

    def _load_taxonomy(self):
        """Load taxonomy and build regex rules"""
        try:
            with open(self.taxonomy_file, 'r') as f:
                taxonomy = yaml.safe_load(f)

            self._build_rules_from_taxonomy(taxonomy)
        except FileNotFoundError:
            # Fallback to default taxonomy if file not found
            self._build_default_taxonomy()

    def _build_rules_from_taxonomy(self, taxonomy: Dict, prefix: str = ""):
        """Recursively build rules from taxonomy structure"""
        for key, value in taxonomy.items():
            current_path = f"{prefix}:{key}" if prefix else key

            if isinstance(value, dict):
                if 'indicators' in value:
                    # This is a leaf node with indicators
                    indicators = value['indicators']
                    self._create_rules_for_indicators(current_path, indicators)
                else:
                    # Continue recursion
                    self._build_rules_from_taxonomy(value, current_path)
            elif isinstance(value, list):
                # Direct list of indicators
                self._create_rules_for_indicators(current_path, value)

    def _create_rules_for_indicators(self, path: str, indicators: List[str]):
        """Create regex rules for taxonomy indicators"""
        patterns = []
        for indicator in indicators:
            # Escape special regex characters and create pattern
            escaped = re.escape(indicator)
            patterns.append(re.compile(escaped, re.IGNORECASE))

        self.rules[path] = {
            'patterns': patterns,
            'weight': 2  # Taxonomy indicators get higher weight
        }

    def _build_default_taxonomy(self):
        """Build default taxonomy if yaml file not available"""
        default_rules = {
            "Test:Failure:Assertion": {
                'patterns': [
                    re.compile(r'AssertionError', re.IGNORECASE),
                    re.compile(r'assert.*failed', re.IGNORECASE),
                    re.compile(r'expected.*got', re.IGNORECASE),
                    re.compile(r'assertion.*failed', re.IGNORECASE)
                ],
                'weight': 2
            },
            "Test:Failure:Timeout": {
                'patterns': [
                    re.compile(r'timeout', re.IGNORECASE),
                    re.compile(r'timed out', re.IGNORECASE),
                    re.compile(r'TimeoutException', re.IGNORECASE)
                ],
                'weight': 2
            },
            "Infra:Network:Timeout": {
                'patterns': [
                    re.compile(r'connection.*timeout', re.IGNORECASE),
                    re.compile(r'network.*timeout', re.IGNORECASE),
                    re.compile(r'read timed out', re.IGNORECASE)
                ],
                'weight': 2
            },
            "Build:Compilation:Error": {
                'patterns': [
                    re.compile(r'compilation.*failed', re.IGNORECASE),
                    re.compile(r'build.*failed', re.IGNORECASE),
                    re.compile(r'compile.*error', re.IGNORECASE)
                ],
                'weight': 2
            }
        }

        # Add generic fallback patterns
        default_rules["UNCLASSIFIED"] = {
            'patterns': [
                re.compile(r'error', re.IGNORECASE),
                re.compile(r'exception', re.IGNORECASE),
                re.compile(r'failed', re.IGNORECASE)
            ],
            'weight': 1
        }

        self.rules = default_rules

    def classify(self, events: List[NormalizedEvent]) -> ClassificationResult:
        """
        Classify events using rule patterns

        Args:
            events: List of normalized log events

        Returns:
            Classification result with label, confidence, and scores
        """
        scores = {}

        # Initialize scores for all rule categories
        for category in self.rules.keys():
            scores[category] = 0

        # Score each event against all patterns
        for event in events:
            text = event.text
            if not text:
                continue

            for category, rule_data in self.rules.items():
                patterns = rule_data['patterns']
                weight = rule_data['weight']

                for pattern in patterns:
                    if pattern.search(text):
                        scores[category] += weight

        # Find best match
        if not any(scores.values()):
            # No matches found
            return ClassificationResult(
                label="UNCLASSIFIED",
                confidence=0.0,
                scores=scores
            )

        # Get category with highest score
        best_category = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_category]
        total_score = sum(scores.values())

        confidence = best_score / total_score if total_score > 0 else 0.0

        return ClassificationResult(
            label=best_category,
            confidence=confidence,
            scores=scores
        )

    def reload_taxonomy(self):
        """Reload taxonomy from file"""
        self._load_taxonomy()

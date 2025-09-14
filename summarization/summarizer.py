"""
Log summarization module
Extracts key information from log events and generates human-readable summaries
"""

import re
from typing import List, Set
from models.pydantic_models import NormalizedEvent, SummaryResult

class LogSummarizer:
    """Extracts and summarizes key information from log events"""

    def __init__(self):
        # Patterns for extracting information
        self.exception_pattern = re.compile(r'(\w*Exception|\w*Error)(?:\s|$|:)', re.IGNORECASE)
        self.assertion_pattern = re.compile(r'(assert.*|AssertionError.*)', re.IGNORECASE)
        self.test_pattern = re.compile(r'test_[a-zA-Z_][a-zA-Z0-9_]*', re.IGNORECASE)

    def summarize(self, events: List[NormalizedEvent]) -> SummaryResult:
        """
        Summarize log events

        Args:
            events: List of normalized log events

        Returns:
            Summary with exceptions, tests, assertions, and human-readable text
        """
        # Focus on recent events (last ~300 lines or all if fewer)
        recent_events = events[-300:] if len(events) > 300 else events

        exceptions = self._extract_exceptions(recent_events)
        tests = self._extract_tests(recent_events)
        assertion = self._extract_assertion(recent_events)

        # Generate human-readable summary
        summary_text = self._generate_summary_text(exceptions, tests, assertion)

        return SummaryResult(
            label="PENDING",  # Will be filled by classifier
            confidence=0.0,   # Will be filled by classifier
            exceptions=exceptions,
            tests=tests,
            assertion=assertion,
            summary=summary_text
        )

    def _extract_exceptions(self, events: List[NormalizedEvent]) -> List[str]:
        """Extract unique exception class names"""
        exceptions: Set[str] = set()

        for event in events:
            if not event.text:
                continue

            matches = self.exception_pattern.findall(event.text)
            for match in matches:
                exceptions.add(match.strip())

                # Limit to first 3 unique exceptions
                if len(exceptions) >= 3:
                    break

            if len(exceptions) >= 3:
                break

        return list(exceptions)

    def _extract_tests(self, events: List[NormalizedEvent]) -> List[str]:
        """Extract test function identifiers"""
        tests: Set[str] = set()

        for event in events:
            if not event.text:
                continue

            matches = self.test_pattern.findall(event.text)
            for match in matches:
                tests.add(match)

                # Limit to 5 distinct tests
                if len(tests) >= 5:
                    break

            if len(tests) >= 5:
                break

        return list(tests)

    def _extract_assertion(self, events: List[NormalizedEvent]) -> str:
        """Extract first assertion message, trimmed to 180 chars"""
        for event in events:
            if not event.text:
                continue

            match = self.assertion_pattern.search(event.text)
            if match:
                assertion = match.group(1).strip()

                # Trim to 180 characters
                if len(assertion) > 180:
                    assertion = assertion[:177] + "..."

                return assertion

        return None

    def _generate_summary_text(self, exceptions: List[str], tests: List[str], assertion: str) -> str:
        """Generate human-readable summary string"""
        parts = []

        # Add exception information
        if exceptions:
            if len(exceptions) == 1:
                parts.append(f"Exception: {exceptions[0]}")
            else:
                parts.append(f"Exceptions: {', '.join(exceptions)}")

        # Add test information
        if tests:
            if len(tests) == 1:
                parts.append(f"Test: {tests[0]}")
            else:
                parts.append(f"Tests: {', '.join(tests[:3])}")  # Show first 3

        # Add assertion if present
        if assertion:
            # Shorten assertion for summary
            short_assertion = assertion[:100] + "..." if len(assertion) > 100 else assertion
            parts.append(f"Assertion: {short_assertion}")

        # Join with pipe separator
        if parts:
            summary = " | ".join(parts)
        else:
            summary = "No specific failure details extracted"

        return summary

    def update_summary_with_classification(self, summary: SummaryResult, 
                                         label: str, confidence: float) -> SummaryResult:
        """Update summary with classification results"""
        summary.label = label
        summary.confidence = confidence

        # Add label to summary text
        summary.summary = f"Label: {label} ({confidence:.2f}) | {summary.summary}"

        return summary

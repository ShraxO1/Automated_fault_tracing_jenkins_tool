"""
Log normalization module
Transforms raw multiline text into structured events
"""

import re
from typing import List
from models.pydantic_models import NormalizedEvent

class LogNormalizer:
    """Normalizes raw build logs into structured events"""

    def __init__(self):
        # ANSI escape code patterns
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        # Noise patterns to filter
        self.noise_patterns = [
            re.compile(r'^\[Pipeline\]'),
            re.compile(r'^\[\d+m'),  # Color codes
            re.compile(r'^Download.*\.\.\.$'),  # Download progress
            re.compile(r'^\s*$'),  # Empty lines
            re.compile(r'^-{5,}$'),  # Separator lines
        ]

        # Timestamp pattern (YYYY-MM-DD HH:MM:SS)
        self.timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

        # Log level patterns
        self.level_pattern = re.compile(r'\[?(INFO|WARN|WARNING|ERROR|DEBUG|TRACE|FATAL)\]?', re.IGNORECASE)

    def normalize(self, raw_log: str) -> List[NormalizedEvent]:
        """
        Normalize raw log text into structured events

        Args:
            raw_log: Raw multiline log text

        Returns:
            List of normalized events with index, timestamp, level, and clean text
        """
        lines = raw_log.split('\n')
        events = []

        for index, line in enumerate(lines):
            # Skip empty lines and noise
            if not line.strip() or self._is_noise(line):
                continue

            # Clean ANSI escape codes
            clean_line = self.ansi_escape.sub('', line).strip()

            if not clean_line:
                continue

            # Extract timestamp
            timestamp = self._extract_timestamp(clean_line)

            # Extract log level
            level = self._extract_level(clean_line)

            # Remove timestamp and level from text for cleaner content
            text = self._clean_text(clean_line, timestamp, level)

            event = NormalizedEvent(
                index=index,
                timestamp=timestamp,
                level=level,
                text=text
            )
            events.append(event)

        return events

    def _is_noise(self, line: str) -> bool:
        """Check if line matches noise patterns"""
        for pattern in self.noise_patterns:
            if pattern.match(line.strip()):
                return True
        return False

    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp from line"""
        match = self.timestamp_pattern.search(line)
        return match.group(1) if match else None

    def _extract_level(self, line: str) -> str:
        """Extract log level from line"""
        match = self.level_pattern.search(line)
        return match.group(1).upper() if match else None

    def _clean_text(self, line: str, timestamp: str, level: str) -> str:
        """Remove timestamp and level from line to get clean text"""
        text = line

        # Remove timestamp
        if timestamp:
            text = text.replace(timestamp, '').strip()

        # Remove level markers
        if level:
            # Remove various level formats: [INFO], INFO, [INFO]
            patterns = [
                f'\[{level}\]',
                f'{level}',
                f'\[{level.lower()}\]',
                f'{level.lower()}'
            ]
            for pattern in patterns:
                text = re.sub(pattern, '', text, count=1)
                text = text.strip()

        # Clean up any remaining brackets or separators at the start
        text = re.sub(r'^[\s\[\]:-]+', '', text).strip()

        return text

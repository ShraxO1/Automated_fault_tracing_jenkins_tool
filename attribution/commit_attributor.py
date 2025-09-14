"""
Commit attribution module
Scores commits against log events to suggest likely culprit commits
"""

import re
from typing import List, Optional
from models.pydantic_models import NormalizedEvent, CommitInfo, AttributionResult

class CommitAttributor:
    """Attributes failures to likely commits using heuristic scoring"""

    def __init__(self):
        # Pattern for extracting file paths from stack traces
        self.file_path_pattern = re.compile(r'File\s+"([^"]+)"', re.IGNORECASE)
        self.stack_trace_pattern = re.compile(r'\s+at\s+([^(]+)\(([^)]+)\)', re.IGNORECASE)

        # Pattern for test names
        self.test_name_pattern = re.compile(r'test_[a-zA-Z_][a-zA-Z0-9_]*')

        # Network/timeout keywords for semantic hints
        self.network_keywords = ['timeout', 'connection', 'network', 'socket', 'http', 'ssl']

    def attribute(self, events: List[NormalizedEvent], 
                 commits: List[CommitInfo]) -> Optional[AttributionResult]:
        """
        Attribute failure to most likely commit

        Args:
            events: Normalized log events
            commits: List of recent commits

        Returns:
            Attribution result with highest scoring commit or None
        """
        if not commits:
            return None

        # Extract relevant information from logs
        stack_files = self._extract_stack_trace_files(events)
        test_names = self._extract_test_names(events)
        has_network_issues = self._detect_network_issues(events)

        # Score each commit
        commit_scores = []

        for commit in commits:
            score = self._score_commit(
                commit, stack_files, test_names, has_network_issues
            )

            commit_scores.append((commit, score))

        # Find highest scoring commit
        commit_scores.sort(key=lambda x: x[1], reverse=True)

        if commit_scores and commit_scores[0][1] > 0:
            best_commit, best_score = commit_scores[0]

            # Find which tests were detected that match this commit
            matching_tests = self._find_matching_tests(best_commit, test_names)

            return AttributionResult(
                sha=best_commit.sha,
                author=best_commit.author,
                score=best_score,
                changed_files=best_commit.changed_files,
                tests_detected=matching_tests
            )

        return None

    def _extract_stack_trace_files(self, events: List[NormalizedEvent]) -> List[str]:
        """Extract file paths from stack traces and error messages"""
        files = set()

        for event in events:
            if not event.text:
                continue

            # Look for file paths in Python-style stack traces
            file_matches = self.file_path_pattern.findall(event.text)
            for file_path in file_matches:
                files.add(file_path.strip())

            # Look for Java-style stack traces  
            stack_matches = self.stack_trace_pattern.findall(event.text)
            for class_method, location in stack_matches:
                if location and '.' in location:
                    # Convert Java class to potential file path
                    potential_file = location.replace('.', '/') + '.java'
                    files.add(potential_file)

        return list(files)

    def _extract_test_names(self, events: List[NormalizedEvent]) -> List[str]:
        """Extract test function names from events"""
        tests = set()

        for event in events:
            if not event.text:
                continue

            test_matches = self.test_name_pattern.findall(event.text)
            for test_name in test_matches:
                tests.add(test_name)

        return list(tests)

    def _detect_network_issues(self, events: List[NormalizedEvent]) -> bool:
        """Check if logs contain network-related issues"""
        for event in events:
            if not event.text:
                continue

            text_lower = event.text.lower()
            for keyword in self.network_keywords:
                if keyword in text_lower:
                    return True

        return False

    def _score_commit(self, commit: CommitInfo, stack_files: List[str], 
                     test_names: List[str], has_network_issues: bool) -> int:
        """
        Score a commit against failure evidence

        Scoring rules:
        - Changed file appears in stack trace: +3 points per file
        - Test name stem matches changed file: +2 points per match  
        - Network issue + network-related file change: +1 point
        """
        score = 0

        # Score file matches in stack traces
        for stack_file in stack_files:
            for changed_file in commit.changed_files:
                if self._files_match(stack_file, changed_file):
                    score += 3

        # Score test name matches with changed files
        for test_name in test_names:
            test_stem = test_name.replace('test_', '')

            for changed_file in commit.changed_files:
                if test_stem.lower() in changed_file.lower():
                    score += 2

        # Bonus for network issues + network-related changes
        if has_network_issues:
            network_related_files = ['network', 'http', 'socket', 'connection', 'timeout', 'retry']

            for changed_file in commit.changed_files:
                file_lower = changed_file.lower()
                for network_term in network_related_files:
                    if network_term in file_lower:
                        score += 1
                        break

        return score

    def _files_match(self, stack_file: str, changed_file: str) -> bool:
        """Check if stack trace file matches a changed file"""
        # Normalize paths for comparison
        stack_normalized = stack_file.replace('\\', '/').lower()
        changed_normalized = changed_file.replace('\\', '/').lower()

        # Direct match
        if stack_normalized == changed_normalized:
            return True

        # Check if one is a suffix of the other (handles relative vs absolute paths)
        if stack_normalized.endswith(changed_normalized) or changed_normalized.endswith(stack_normalized):
            return True

        # Extract filename and check match
        stack_filename = stack_normalized.split('/')[-1]
        changed_filename = changed_normalized.split('/')[-1]

        return stack_filename == changed_filename

    def _find_matching_tests(self, commit: CommitInfo, test_names: List[str]) -> List[str]:
        """Find test names that likely relate to the commit's changes"""
        matching_tests = []

        for test_name in test_names:
            test_stem = test_name.replace('test_', '')

            # Check if test relates to changed files
            for changed_file in commit.changed_files:
                if test_stem.lower() in changed_file.lower():
                    matching_tests.append(test_name)
                    break

        return matching_tests

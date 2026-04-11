"""
Grading system for data cleaning tasks.
Evaluates agent performance based on issue resolution and data quality.
"""

from typing import Dict, List, Any, Tuple
from .utils import detect_issues

# Use 0.001 as minimum — 1e-6 rounds to 0.0000 at 4 decimal places and FAILS validation
EPS = 1e-3   # Strictly between 0 and 1

def safe_score(score: float) -> float:
    if score <= 0:
        return EPS
    if score >= 1:
        return 1 - EPS
    return round(score, 4)

def _clamp(score: float) -> float:
    return safe_score(score)


def grade_easy(data: List[Dict[str, Any]]) -> float:
    """
    Grade the easy task: simple missing value imputation.
    Success: All missing ages filled.
    """
    issues = detect_issues(data)
    issue_types = {issue["type"] for issue in issues}

    score = 0.0

    if "missing_age" not in issue_types:
        score += 0.6
    if "invalid_email" not in issue_types:
        score += 0.2
    if "duplicates" not in issue_types:
        score += 0.2

    return _clamp(score)


def grade_medium(data: List[Dict[str, Any]]) -> float:
    """
    Grade the medium task: mixed issue fixing.
    Success: Missing values + format errors resolved.
    """
    issues = detect_issues(data)
    issue_types = {issue["type"] for issue in issues}

    score = 0.0

    if "missing_age" not in issue_types:
        score += 0.3
    if "invalid_email" not in issue_types:
        score += 0.3
    if "wrong_type" not in issue_types:
        score += 0.2
    if "duplicates" not in issue_types:
        score += 0.2

    return _clamp(score)


def grade_hard(data: List[Dict[str, Any]]) -> float:
    """
    Grade the hard task: all major issue types must be resolved.
    """
    issues = detect_issues(data)
    issue_types = {issue["type"] for issue in issues}

    score = 0.0

    if "missing_age" not in issue_types:
        score += 0.25
    if "invalid_email" not in issue_types:
        score += 0.25
    if "wrong_type" not in issue_types:
        score += 0.25
    if "duplicates" not in issue_types:
        score += 0.25

    return _clamp(score)


def grade_sprint(data: List[Dict[str, Any]]) -> float:
    """Grade sprint: tricky edge cases need perfect handling."""
    issues = detect_issues(data)
    issue_types = {issue["type"] for issue in issues}

    score = 0.0

    if "missing_age" not in issue_types:
        score += 0.2
    if "invalid_email" not in issue_types:
        score += 0.25
    if "wrong_type" not in issue_types:
        score += 0.25
    if "duplicates" not in issue_types:
        score += 0.15
    # Bonus for clean data overall
    if len(issues) == 0:
        score += 0.15

    return _clamp(score)


def grade_nightmare(data: List[Dict[str, Any]]) -> float:
    """Grade nightmare: catastrophic corruption needs heroic cleanup."""
    issues = detect_issues(data)
    issue_types = {issue["type"] for issue in issues}
    total_issues = len(issues)

    score = 0.0

    if "missing_age" not in issue_types:
        score += 0.2
    if "invalid_email" not in issue_types:
        score += 0.2
    if "wrong_type" not in issue_types:
        score += 0.2
    if "duplicates" not in issue_types:
        score += 0.2
    # Bonus for near-zero remaining issues
    if total_issues <= 1:
        score += 0.2
    elif total_issues <= 3:
        score += 0.1

    return _clamp(score)


def grade(task: str, data: List[Dict[str, Any]]) -> float:
    if task == "easy":
        return grade_easy(data)
    elif task == "medium":
        return grade_medium(data)
    elif task == "hard":
        return grade_hard(data)
    elif task == "sprint":
        return grade_sprint(data)
    elif task == "nightmare":
        return grade_nightmare(data)
    else:
        return SCORE_MIN


def get_issue_breakdown(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Get detailed breakdown of issues in dataset.

    Returns:
        Dictionary with issue counts
    """
    issues = detect_issues(data)
    breakdown: Dict[str, int] = {}

    for issue in issues:
        issue_type = issue["type"]
        breakdown[issue_type] = breakdown.get(issue_type, 0) + 1

    return breakdown


def calculate_quality_score(
    task: str,
    initial_issues: int,
    final_issues: int,
    steps_taken: int,
    rewards: List[float]
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate comprehensive quality score.

    Combines:
    - Issue reduction (0.5 weight)
    - Reward accumulation (0.3 weight)
    - Efficiency bonus (0.2 weight)
    """
    metrics = {
        "task": task,
        "initial_issues": initial_issues,
        "final_issues": final_issues,
        "steps_taken": steps_taken,
        "total_reward": sum(rewards) if rewards else 0.0,
        "avg_reward": sum(rewards) / len(rewards) if rewards else 0.0,
    }

    # Component 1: Issue reduction (50% weight)
    if initial_issues > 0:
        issue_reduction = (initial_issues - final_issues) / initial_issues
    else:
        issue_reduction = 1.0 if final_issues == 0 else 0.0

    issue_score = min(max(issue_reduction, 0.0), 1.0) * 0.5

    # Component 2: Reward accumulation (30% weight)
    max_reward = 15.0
    reward_score = min(max(sum(rewards) / max_reward if rewards else 0.0, 0.0), 1.0) * 0.3

    # Component 3: Efficiency (20% weight)
    expected_steps = {"easy": 3, "medium": 5, "hard": 8}
    max_steps_allowed = expected_steps.get(task, 5) * 2
    efficiency = max(1.0 - (steps_taken / max_steps_allowed), 0.0)
    efficiency_score = efficiency * 0.2

    final_score = issue_score + reward_score + efficiency_score
    metrics["score"] = _clamp(final_score)

    return metrics["score"], metrics
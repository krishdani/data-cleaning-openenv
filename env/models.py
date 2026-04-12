from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, Any

class CodeReviewTask(BaseModel):
    code: str
    rubric: Any

class RewardState(BaseModel):
    score: float
    verdict: str
    matched_keywords: List[str]
    missing_keywords: List[str]
    partial_keywords: List[str]
    semantic_overlap: float
    rationale: str

from .grader import clamp_strict_score

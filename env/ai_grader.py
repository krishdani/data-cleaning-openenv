"""AI-powered grading using Gemini to evaluate code reviews intelligently."""
from __future__ import annotations

import json
import os
import re
from typing import Any

try:
    from google import genai
except ImportError:
    genai = None

from .models import CodeReviewTask, RewardState, clamp_strict_score


GRADING_PROMPT = """You are an expert code review grader. Given a piece of buggy code, the expected explanation, and a student's review, evaluate how well the student identified the bug and suggested a fix.

BUGGY CODE:
{code}

EXPECTED EXPLANATION:
{expected_explanation}

STUDENT'S REVIEW:
{student_review}

Score the review on this scale:
- 1.0 = The review correctly identifies the core bug AND suggests the right fix direction
- 0.5 = The review partially identifies the issue OR mentions the fix but misses key details
- 0.0 = The review completely misses the actual bug

Respond with ONLY valid JSON, no markdown, no code fences:
{{"score": <0.0 or 0.5 or 1.0>, "verdict": "<full_match or partial_match or wrong>", "rationale": "<1-2 sentence explanation of your grading>", "matched_signals": ["<key concepts the student got right>"], "missing_signals": ["<key concepts the student missed>"]}}"""


def ai_grade_review(task: CodeReviewTask, review: str) -> RewardState | None:
    """Use Gemini to intelligently grade a review. Returns None if AI is unavailable."""
    # Try multiple API key names for cross-project compatibility
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not genai or not api_key:
        return None

    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        client = genai.Client(api_key=api_key)

        prompt = GRADING_PROMPT.format(
            code=task.code,
            expected_explanation=task.rubric.explanation if hasattr(task.rubric, 'explanation') else str(task.rubric),
            student_review=review,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        result = json.loads(raw)

        raw_score = float(result.get("score", 0.0))
        # Use strictly valid scores
        if raw_score >= 0.9:
            score = 0.99
            verdict = "full_match"
        elif raw_score >= 0.25:
            score = 0.5
            verdict = "partial_match"
        else:
            score = 0.01
            verdict = "wrong"

        return RewardState(
            score=score,
            verdict=verdict,
            matched_keywords=result.get("matched_signals", []),
            missing_keywords=result.get("missing_signals", []),
            partial_keywords=[],
            semantic_overlap=score,
            rationale=result.get("rationale", "AI-evaluated review."),
        )
    except Exception as exc:
        print(f"[WARN] AI grading failed, falling back to keyword grading: {exc}")
        return None


FIX_GRADING_PROMPT = """You are an expert code reviewer evaluating a student's attempt to fix a buggy piece of code.

ORIGINAL BUGGY CODE:
{original_code}

EXPECTED FIX / CORE ISSUE:
{expected_explanation}

STUDENT'S SUBMITTED FIX:
{fixed_code}

Score the fixed code on this scale:
- 1.0 = The student correctly fixed the core bug without introducing new errors.
- 0.5 = The student partially addressed the issue but missed edge cases or introduced minor bugs.
- 0.0 = The student did not fix the bug or broke the intended functionality.

Respond with ONLY valid JSON, no markdown, no code fences:
{{"score": <0.0 or 0.5 or 1.0>, "verdict": "<full_match or partial_match or wrong>", "rationale": "<1-2 sentence explanation of your grading>", "matched_signals": ["<what they fixed correctly>"], "missing_signals": ["<what they missed or broke>"]}}"""


def ai_grade_fix(task: CodeReviewTask, fixed_code: str) -> RewardState | None:
    """Use Gemini to grade a submitted code fix."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not genai or not api_key:
        return None

    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        client = genai.Client(api_key=api_key)

        prompt = FIX_GRADING_PROMPT.format(
            original_code=task.code,
            expected_explanation=task.rubric.explanation if hasattr(task.rubric, 'explanation') else str(task.rubric),
            fixed_code=fixed_code,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        raw = response.text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)

        raw_score = float(result.get("score", 0.0))
        if raw_score >= 0.9:
            score = 0.99
            verdict = "full_match"
        elif raw_score >= 0.25:
            score = 0.5
            verdict = "partial_match"
        else:
            score = 0.01
            verdict = "wrong"

        return RewardState(
            score=score,
            verdict=verdict,
            matched_keywords=result.get("matched_signals", []),
            missing_keywords=result.get("missing_signals", []),
            partial_keywords=[],
            semantic_overlap=score,
            rationale=result.get("rationale", "AI-evaluated fix."),
        )
    except Exception as exc:
        print(f"[WARN] AI fix grading failed: {exc}")
        return None

AUDITOR_PROMPT = """You are a strict, veteran Senior Security Auditor known for finding edge cases everyone else misses. 
A junior developer has reviewed some buggy code. I need you to evaluate their review.

BUGGY CODE:
{code}

JUNIOR'S REVIEW:
{student_review}

Analyze the review. Do you agree with it? Did they miss any deeper underlying issues, security risks, or edge cases?
Respond in 2-4 sentences max. Be direct, authoritative, and slightly critical but constructive. Do not use markdown. Do not write code."""

def ai_second_opinion(task: CodeReviewTask, student_review: str) -> str:
    """Use Gemini with a strict auditor persona to critique a review."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not genai or not api_key:
        return "I cannot provide a second opinion because the AI backend is currently unavailable."

    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        client = genai.Client(api_key=api_key)

        prompt = AUDITOR_PROMPT.format(
            code=task.code,
            student_review=student_review,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        return response.text.strip()
    except Exception as exc:
        print(f"[WARN] AI second opinion failed: {exc}")
        return f"The auditor is currently unavailable: {exc}"

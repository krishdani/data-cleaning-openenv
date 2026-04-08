"""
FastAPI backend for Data Cleaning OpenEnv (Gemini-ready).
Supports deterministic and LLM (Gemini) agents for real-world data cleaning.
"""
from __future__ import annotations
# Version 1.2.1-final-verification
import os
import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Body, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from dotenv import load_dotenv
import csv
import io
import re
import google.generativeai as genai

from env import DataCleaningEnv, TASKS, grade
from env.schemas import Action, Observation, StepResponse, ResetResponse
from env.grader import calculate_quality_score

# Load environment variables
load_dotenv()

def _is_int_like(value: Any) -> bool:
    if isinstance(value, int):
        return True
    if isinstance(value, str) and value.isdigit():
        return True
    return False

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Data Cleaning OpenEnv",
    version="1.2.0",
    description="Hackathon Workspace: Interactive Data Cleaning & Manual Audits.",
)

# Robust CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug helper for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import sys
    print(f"Validation Error at {request.url.path}: {exc.errors()}", file=sys.stderr)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

# ---------------------------------------------------------------------------
# Global State
# ---------------------------------------------------------------------------
_env: Optional[DataCleaningEnv] = None
_original_data: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class ResetRequest(BaseModel):
    task: str = Field("easy", validation_alias=AliasChoices("task", "dataset_name"))
    mode: str = "baseline"
    model_config = ConfigDict(populate_by_name=True)

class AuditRequest(BaseModel):
    user_input: str = Field(..., description="The issues identified by the user manually")

class StepRequest(BaseModel):
    action: str = Field(..., description="The action to apply")
    message: Optional[str] = Field(None, description="Optional reasoning or details")

class DatasetInfo(BaseModel):
    name: str
    task: str
    description: str
    row_count: int
    issue_count: int

class CleanRunResponse(BaseModel):
    task: str
    original_data: List[Dict[str, Any]]
    final_data: List[Dict[str, Any]]
    actions: List[str]
    rewards: List[float]
    score: float
    grade: float
    steps_log: List[Dict[str, Any]]
    final_issues: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    model_used: str

# ---------------------------------------------------------------------------
# Gemini Agent & Reviewer
# ---------------------------------------------------------------------------
def repair_json(s: str) -> str:
    """Attempt to repair common JSON truncation issues."""
    s = s.strip()
    if not s: return "{}"
    if s.count('{') > s.count('}'):
        s += '}' * (s.count('{') - s.count('}'))
    if s.count('"') % 2 != 0:
        if s.endswith('}'):
            s = s[:-1] + '"}'
        else:
            s += '"}'
    return s

def gemini_call(prompt: str, max_tokens: int = 1000) -> str:
    """Utility for calling Gemini using Native SDK or OpenAI fallback."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or "your-gemini" in api_key:
        return "error: missing key"
    
    try:
        # Layer 1: Native Google SDK
        genai.configure(api_key=api_key)
        model_ids = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        resp = None
        
        for m_id in model_ids:
            try:
                model = genai.GenerativeModel(m_id)
                resp = model.generate_content(
                    prompt, 
                    generation_config={"max_output_tokens": max_tokens, "temperature": 0.1}
                )
                if resp: break
            except: continue
        
        if resp and hasattr(resp, "text") and resp.text:
            return resp.text.strip()
            
        raise Exception("Native SDK failed or blocked")
        
    except Exception as e1:
        # Layer 2: OpenAI-Compatible Endpoint Fallback (v1beta stable)
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            response = client.chat.completions.create(
                model="gemini-1.5-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1
            )
            content = response.choices[0].message.content
            if content: return content.strip()
            raise Exception("Empty Response")
        except Exception as e2:
            return f"error: SDK({str(e1)}) | HTTP({str(e2)})"

def gemini_agent_decision(observation: Dict[str, Any], previous_actions: List[str], task: str) -> str:
    """Use Gemini to choose the next cleaning action."""
    issues = observation.get("issues", [])
    prompt = f"Data Cleaning Agent Task. Issues: {json.dumps(issues[:5])}. Task: {task}. Previous: {previous_actions}. Next action (fix_email, convert_age, fill_missing_age, remove_duplicates, drop_invalid)? Respond with ONLY the action name."
    chosen = gemini_call(prompt, 15).lower()
    valid = {"fix_email", "convert_age", "fill_missing_age", "remove_duplicates", "drop_invalid"}
    return chosen if chosen in valid else "deterministic_fallback"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": "OpenEnv Data Cleaning"}

@app.get("/api/diagnostics")
@app.get("/diagnostics")
def get_diagnostics():
    key = os.getenv("OPENAI_API_KEY", "")
    return {
        "status": "online",
        "gemini_api_key": "Set" if key and "your-gemini" not in key else "Missing",
        "model": os.getenv("MODEL_NAME", "gemini-1.5-flash"),
        "base_url": os.getenv("API_BASE_URL", "Native SDK Active"),
        "tasks": list(TASKS.keys())
    }

@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    global _env, _original_data
    content = await file.read()
    filename = file.filename or "uploaded.csv"
    
    try:
        if filename.endswith(".csv"):
            decoded = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
            data = [row for row in reader]
        elif filename.endswith(".json"):
            data = json.loads(content)
        else:
            raise HTTPException(status_code=400, detail="Only CSV or JSON allowed.")
        
        _env = DataCleaningEnv(task="custom", data=data)
        reset_resp = _env.reset()
        _original_data = [dict(r) for r in reset_resp.observation.data]
        return {"status": "success", "task": "custom", "row_count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def calculate_reward(score: float) -> Dict[str, Any]:
    """Calculate hackathon rewards based on audit score."""
    if score >= 1.0:
        return {"tier": "Grand Slam", "points": 1000, "message": "🟡 GOLD MEDAL: Perfect Audit! You're a Data Engineering Pro."}
    elif score >= 0.8:
        return {"tier": "Expert", "points": 500, "message": "⚪ SILVER MEDAL: Excellent work. You caught almost everything."}
    elif score >= 0.5:
        return {"tier": "Contributor", "points": 200, "message": "🟤 BRONZE MEDAL: Good effort. There's still room to improve."}
    else:
        return {"tier": "Novice", "points": 50, "message": "🔵 NOVICE: Keep practicing. Data cleaning takes a sharp eye!"}

@app.post("/api/review-input")
def review_user_audit(req: AuditRequest) -> Dict[str, Any]:
    global _env
    if not _env:
        raise HTTPException(status_code=400, detail="Initialize a task first.")
    
    state = _env.state()
    issues = state.issues
    original_data = [dict(r) for r in state.data]

    import re
    from difflib import SequenceMatcher

    def normalize(text):
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return text

    def similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()

    def calculate_score(user_issues, expected_issues):
        matched_score = 0
        used_expected = set()

        for user_issue in user_issues:
            user_issue = normalize(user_issue)

            best_match = 0
            best_idx = -1

            for i, expected in enumerate(expected_issues):
                if i in used_expected:
                    continue

                expected_norm = normalize(expected)
                sim = similarity(user_issue, expected_norm)

                if sim > best_match:
                    best_match = sim
                    best_idx = i

            if best_match > 0.75:
                matched_score += 1
                used_expected.add(best_idx)

            elif best_match > 0.45:
                matched_score += 0.5
                used_expected.add(best_idx)

        total = len(expected_issues)

        if total == 0:
            return 0, 0

        score = (matched_score / total) * 100
        score = round(score)

        return score, matched_score

    def get_reward(score):
        # Convert score (0–100) → reward (-1 to 1)
        reward = (score / 50) - 1

        # Clamp safely
        reward = max(-1.0, min(1.0, reward))

        return round(reward, 3)

    def get_tier(score):
        if score >= 90:
            return "elite"
        elif score >= 75:
            return "pro"
        elif score >= 50:
            return "intermediate"
        elif score >= 25:
            return "basic"
        else:
            return "low"

    expected_issues = []
    for issue in issues:
        r = str(issue.get("row", ""))
        c = str(issue.get("column", "")).lower()
        t = str(issue.get("type", "")).lower().replace("_", " ")
        expected_issues.append(f"row {r} {c} {t}")

    user_issues = [x.strip() for x in req.user_input.split(",")]

    score, matched = calculate_score(user_issues, expected_issues)
    reward = get_reward(score)
    tier = get_tier(score)

    critique = f"Matched {matched:.1f}/{len(expected_issues)} issues ({score}%)."

    # Gather Stats for Graphs
    ages = [r.get("age") for r in original_data if _is_int_like(r.get("age"))]
    stats = {
        "age_dist": {str(a): ages.count(a) for a in set(ages) if a is not None},
        "issue_types": {iss["type"]: 0 for iss in issues}
    }
    for iss in issues:
        stats["issue_types"][iss["type"]] += 1

    # Simulate cleaning to produce Verified Dataset
    temp_env = DataCleaningEnv(task=_env.task, data=[dict(r) for r in original_data])
    for action_name in ["fix_email", "convert_age", "fill_missing_age", "remove_duplicates", "fill_missing"]:
        temp_env.step(Action(action=action_name))
        if temp_env.done: break

    return {
        "score": score,
        "reward": reward,
        "tier": tier,
        "critique": critique,
        "stats": stats,
        "final_data": [dict(r) for r in temp_env.state().data],
        "explanation": "Expert review processed via RL-aligned semantic matching."
    }

@app.post("/reset")
@app.post("/api/reset")
def reset_env(req: Optional[ResetRequest] = None) -> Dict[str, Any]:
    global _env, _original_data
    if req is None:
        req = ResetRequest()
    _env = DataCleaningEnv(task=req.task)
    resp = _env.reset()
    _original_data = [dict(r) for r in resp.observation.data]
    return resp.model_dump()

@app.get("/api/original-data")
def get_original_data():
    return _original_data

@app.post("/step")
@app.post("/api/step")
def step_env(req: StepRequest = Body(...)) -> Dict[str, Any]:
    global _env
    if not _env:
        _env = DataCleaningEnv(task="easy")
    
    action = Action(action=req.action, message=req.message)
    resp = _env.step(action)
    return resp.model_dump()

@app.get("/state")
@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    global _env
    if not _env:
        _env = DataCleaningEnv(task="easy")
    return _env.state().model_dump()

@app.post("/api/clean")
def run_full_pipeline(req: ResetRequest) -> CleanRunResponse:
    global _env
    if req.task != "custom" and req.task not in TASKS:
        raise HTTPException(status_code=400, detail=f"Task '{req.task}' unknown.")

    # Use current custom env if it exists and task matches, else init new
    if req.task == "custom" and _env and _env.task == "custom":
        env = _env
    else:
        env = DataCleaningEnv(task=req.task)
    
    reset_resp = env.reset()
    original_data = [dict(r) for r in reset_resp.observation.data]
    initial_issues = len(reset_resp.observation.issues)

    actions: List[str] = []
    rewards: List[float] = []
    steps_log: List[Dict[str, Any]] = []
    
    priority = ["fix_email", "convert_age", "fill_missing_age", "remove_duplicates", "drop_invalid"]

    for i in range(1, 11):
        obs = {"issues": [dict(iss) for iss in env.state().issues], "data": [dict(r) for r in env.state().data]}
        
        # Decide Action (Prioritize Gemini for Baseline)
        action_name = "none"
        ai_action = gemini_agent_decision(obs, actions, req.task)
        if ai_action != "deterministic_fallback" and "error:" not in ai_action:
            action_name = ai_action
        else:
            action_name = next((a for a in priority if a not in actions), "drop_invalid")

        # Step
        resp = env.step(Action(action=action_name))
        actions.append(action_name)
        rewards.append(resp.reward)
        steps_log.append({
            "step": i,
            "action": action_name,
            "reward": resp.reward,
            "done": resp.done,
            "issues_remaining": len(resp.observation.issues)
        })
        if resp.done: break

    final_obs = env.state()
    score, metrics = calculate_quality_score(req.task, initial_issues, len(final_obs.issues), len(actions), rewards)

    return CleanRunResponse(
        task=req.task,
        original_data=original_data,
        final_data=[dict(r) for r in final_obs.data],
        actions=actions,
        rewards=rewards,
        score=score,
        grade=grade(req.task, [dict(r) for r in final_obs.data]),
        steps_log=steps_log,
        final_issues=[dict(iss) for iss in final_obs.issues],
        metrics=metrics,
        model_used="gemini-1.5-flash"
    )

@app.get("/api/tasks")
def get_tasks() -> List[DatasetInfo]:
    res = []
    for t_id, t_info in TASKS.items():
        env_temp = DataCleaningEnv(task=t_id)
        s = env_temp.state()
        res.append(DatasetInfo(name=t_info["name"], task=t_id, description=t_info["description"], row_count=len(s.data), issue_count=len(s.issues)))
    return res

@app.get("/health")
def health(): return {"status": "ok"}

# Static Frontend
FRONTEND_BUILD = Path(__file__).parent / "frontend" / "out"
if FRONTEND_BUILD.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD), html=True), name="frontend")
else:
    @app.get("/")
    def index(): return {"message": "Server online. Frontend build not found at /frontend/out"}

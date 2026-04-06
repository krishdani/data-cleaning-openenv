"""
FastAPI backend for Data Cleaning OpenEnv (Gemini-ready).
Supports deterministic and LLM (Gemini) agents for real-world data cleaning.
"""
from __future__ import annotations
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

from env import DataCleaningEnv, TASKS, grade
from env.schemas import Action, Observation, StepResponse, ResetResponse
from env.grader import calculate_quality_score

# Load environment variables
load_dotenv()

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
def gemini_call(prompt: str, max_tokens: int = 200) -> str:
    """Utility for calling Gemini."""
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        model = os.getenv("MODEL_NAME", "gemini-1.5-flash")
        
        # Use model name directly for OpenAI compatibility endpoint
        
        if not api_key or "your-gemini" in api_key:
            return "error: missing key"

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"error: {str(e)}"

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

@app.get("/api/diagnostics")
def get_diagnostics():
    key = os.getenv("OPENAI_API_KEY", "")
    return {
        "gemini_api_key": "Set" if key and "your-gemini" not in key else "Missing",
        "api_base": os.getenv("API_BASE_URL"),
        "model": os.getenv("MODEL_NAME"),
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

@app.post("/api/review-input")
def review_user_audit(req: AuditRequest) -> Dict[str, Any]:
    global _env
    if not _env:
        raise HTTPException(status_code=400, detail="Initialize a task first.")
    
    state = _env.state()
    issues = state.issues
    
    prompt = f"Review this user's audit of a dataset. GROUND TRUTH ISSUES: {json.dumps([dict(i) for i in issues])}. USER AUDIT: '{req.user_input}'. Is the user's audit accurate? Provide a score (0.0 to 1.0) and a short critique (1 sentence). Return as JSON: {{\"score\": 0.8, \"critique\": \"...\"}}"
    raw_review = gemini_call(prompt)
    
    try:
        # Simple extraction if model returns markdown/text
        review_clean = raw_review.strip()
        if "```json" in review_clean:
            review_clean = review_clean.split("```json")[1].split("```")[0]
        return json.loads(review_clean)
    except:
        return {"score": 0.0, "critique": f"Failed to parse AI review: {raw_review}"}

@app.post("/reset")
@app.post("/api/reset")
def reset_env(req: ResetRequest = Body(...)) -> Dict[str, Any]:
    global _env, _original_data
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

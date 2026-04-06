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
import google.generativeai as genai

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
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or "your-gemini" in api_key:
        return "error: missing key"
    
    try:
        # Try Native Google SDK First (More reliable)
        genai.configure(api_key=api_key)
        model_name = os.getenv("MODEL_NAME", "gemini-1.5-flash").strip()
        model_id = model_name.replace("models/", "")
        
        model = genai.GenerativeModel(model_id)
        # Disable all safety filters to prevent truncation on participant names
        safety = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.2
            ),
            safety_settings=safety
        )
        return response.text.strip() if response.text else "error: empty response"
    except Exception as native_e:
        if "429" in str(native_e):
            return "error: API Rate Limit reached. Please wait 60 seconds and try again."
        # Fallback to OpenAI Client
        try:
            from openai import OpenAI
            base_url = os.getenv("API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
            client = OpenAI(api_key=api_key, base_url=base_url)
            model_name = os.getenv("MODEL_NAME", "gemini-1.5-flash").strip()
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": f"Return ONLY raw JSON.\n\n{prompt}"}],
                max_tokens=max_tokens,
                temperature=0.2
            )
            content = response.choices[0].message.content
            return content.strip() if content else "error: empty response"
        except Exception as openai_e:
            return f"error: Native: {str(native_e)} | OpenAI: {str(openai_e)}"

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
    
    prompt = (
        "You must return ONLY valid JSON.\n"
        "Format EXACTLY like this:\n"
        "{\n"
        "  \"score\": <number between -1 and 1>,\n"
        "  \"critique\": \"<short explanation>\"\n"
        "}\n"
        "Rules:\n"
        "- Do NOT add extra text\n"
        "- Do NOT break JSON\n"
        "- Always close brackets\n"
        "- Always include both fields\n\n"
        f"GROUND TRUTH: {json.dumps([dict(i) for i in issues])}\n"
        f"USER AUDIT: '{req.user_input}'"
    )
    raw_review = gemini_call(prompt, max_tokens=1000)
    
    try:
        # Robust cleanup
        clean = raw_review.strip()
        if "```" in clean: clean = clean.split("```")[1] if "```" in clean else clean
        if "json" in clean[:10]: clean = clean.replace("json", "", 1).strip()
        
        # Handle single quotes
        if "'" in clean and '"' not in clean:
            clean = clean.replace("'", '"')

        # Find first { and last }
        start = clean.find("{")
        end = clean.rfind("}")
        
        if start != -1:
            if end == -1 or end <= start: # Truncated
                json_str = repair_json(clean[start:])
            else:
                json_str = clean[start:end+1]
            return json.loads(json_str)
            
        return json.loads(clean)
    except Exception as e:
        # If it's an error from gemini_call, report it directly
        if raw_review.startswith("error:"):
            return {"score": 0.0, "critique": f"AI Error: {raw_review[6:100]}"}
        
        # Last ditch effort: try repair with current clean string
        try:
            return json.loads(repair_json(clean))
        except:
            return {"score": 0.0, "critique": f"AI Parsing Error: {str(e)} | Content: {raw_review[:40]}"}

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

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
        model_name = os.getenv("MODEL_NAME", "gemini-1.5-flash").strip()
        # Ensure we use a stable model ID format
        model_id = model_name.replace("models/", "")
        model = genai.GenerativeModel(model_id)
        
        resp = model.generate_content(
            prompt, 
            generation_config={"max_output_tokens": max_tokens, "temperature": 0.1},
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        
        if hasattr(resp, "text") and resp.text:
            return resp.text.strip()
        if resp.candidates:
            cand = resp.candidates[0]
            if cand.content and cand.content.parts:
                return cand.content.parts[0].text.strip()
        
        # If we got here, it's likely a safety block or empty response
        reason = resp.candidates[0].finish_reason.name if resp.candidates else "Unknown"
        raise Exception(f"Native Blocked: {reason}")
        
    except Exception as e1:
        # Layer 2: OpenAI-Compatible Endpoint Fallback
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1/openai/"
            )
            response = client.chat.completions.create(
                model="gemini-1.5-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1
            )
            content = response.choices[0].message.content
            if content:
                return content.strip()
            raise Exception("Empty OpenAI response")
        except Exception as e2:
            detail = f"SDK Error: {str(e1)} | HTTP Error: {str(e2)}"
            # Return special error prefix so caller knows to use local fallback
            return f"error: {detail}"

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
    
    prompt = f"""
Audit the following dataset based on the user's manual report.
Task: {_env.task} - {TASKS.get(_env.task, {}).get('name', 'Cleaning Task')}

Ground Truth Issues In Dataset:
{json.dumps([dict(i) for i in issues])}

User's Manual Audit Findings:
"{req.user_input}"

    Scoring Rubric (Strict JSON Response):
    1. Identification Accuracy: Did they find the specific rows/fields with issues?
    2. Reasoning: Does their explanation make sense for that data type?
    3. FALSE ALARMS: Did they report something that is NOT an issue? If yes, use a NEGATIVE score.

    Rules for score:
    - Excellent: 0.7 to 1.0
    - Mostly correct: 0.4 to 0.6
    - Mixed/Vague: 0.1 to 0.3
    - No findings or vague: 0.0
    - WRONG / FALSE ALARMS: -0.1 to -1.0 (Critical Penalty)

    Return a STRICT JSON object:
    {{
      "score": <float -1.0 to 1.0>,
      "critique": "<short 1-2 sentence feedback analyzing their finding>"
    }}
    """
    raw_review = gemini_call(prompt, max_tokens=1000)
    
    res = {}
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
            res = json.loads(json_str)
        else:
            res = json.loads(clean)
    except Exception as e:
        # DETERMINISTIC FUZZY EVALUATOR (FALLBACK)
        user_lower = req.user_input.lower()
        found_matches = 0
        total_gt = len(issues)
        
        for issue in issues:
            match = False
            row_idx = str(issue.get('row', -1))
            k_col = str(issue.get('column', '')).lower()
            k_type = str(issue.get('type', '')).lower().replace("_", " ")
            
            # Match by Row Number
            if row_idx != "-1" and (row_idx in user_lower or f"row {row_idx}" in user_lower or f"{row_idx} row" in user_lower):
                match = True
            
            # Match by Column Name
            if k_col != "none" and k_col in user_lower:
                match = True
            
            # Match by Issue Type keyword
            if len(k_type) > 2 and k_type in user_lower:
                match = True
            
            # Match by semantic keywords
            if "missing" in user_lower and ("missing" in k_type or "null" in k_type):
                match = True
            if "format" in user_lower and "format" in k_type:
                match = True

            # Match by values in that row
            row_data = next((r for i, r in enumerate(original_data) if i == issue.get('row')), {})
            for val in row_data.values():
                if val and str(val).lower() in user_lower and len(str(val)) > 3:
                    match = True
                    break
            
            if match: found_matches += 1
        
        # Boosted Fallback Score [0.0 - 1.0]
        if found_matches > 0:
            raw_acc = found_matches / total_gt if total_gt > 0 else 0.0
            fallback_score = round(max(0.25, min(1.0, 0.2 + (raw_acc * 1.5))), 2)
        else:
            fallback_score = 0.0
            
        res = {
            "score": fallback_score, 
            "critique": f"Deep Diagnostic: You successfully identified {found_matches} of {total_gt} dataset issues. {raw_review if raw_review.startswith('error:') else ''}"
        }
    
    # Ensure score is numeric
    try:
        raw_score = res.get("score", 0.0)
        res["score"] = float(raw_score)
    except (TypeError, ValueError):
        res["score"] = 0.0

    # Ensure score is within [-1, 1] range as requested
    res["score"] = max(-1.0, min(1.0, res["score"]))

    # Always add reward to the response
    res["reward"] = calculate_reward(res.get("score", 0.0))
    
    # Run a quick automated cleaning session to show the "After" state for this audit
    temp_env = DataCleaningEnv(task=_env.task, data=[dict(r) for r in original_data])
    priority = ["fix_email", "convert_age", "fill_missing_age", "remove_duplicates", "drop_invalid"]
    for action_name in priority:
        temp_env.step(Action(action=action_name))
        if temp_env.done: break
        
    res["final_data"] = [dict(r) for r in temp_env.state().data]

    # Added stats for graphs
    ages = [r.get("age") for r in original_data if _is_int_like(r.get("age"))]
    res["stats"] = {
        "age_dist": {str(a): ages.count(a) for a in set(ages) if a is not None},
        "issue_types": {iss["type"]: 0 for iss in issues}
    }
    for iss in issues:
        res["stats"]["issue_types"][iss["type"]] += 1

    # Final response assembly (ensure premium data format)
    return {
        "score": res.get("score", 0.0),
        "critique": res.get("critique") or "Expert Review Complete: Audit processed successfully.",
        "reward": res.get("reward") if res.get("reward") else calculate_reward(res.get("score", 0.0)),
        "final_data": res.get("final_data", []),
        "stats": res.get("stats", {}),
        "explanation": res.get("explanation", "AI context unavailable (Rate limit or API issue). Detailed results shown below.")
    }

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

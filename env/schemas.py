from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Literal

class DataIssue(BaseModel):
    row: int
    column: str | None = None
    type: str

class Observation(BaseModel):
    data: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    echoed_message: str | None = None
    
    model_config = ConfigDict(extra="allow")

class Action(BaseModel):
    message: str | None = None
    action: Literal["remove_duplicates", "fill_missing_age", "fix_email", "convert_age", "drop_invalid"] | str | None = None

class Reward(BaseModel):
    value: float
    reason: str | None = None

class Info(BaseModel):
    error: str | None = None
    metrics: Dict[str, float] | None = None

class StepResponse(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: Info

class ResetResponse(BaseModel):
    observation: Observation

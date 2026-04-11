from typing import Any, Dict, List, Tuple
from .utils import generate_dirty_data, detect_issues
from .actions import remove_duplicates, fill_missing_age, fix_email, convert_age, drop_invalid
from .schemas import Observation, Action, Info, StepResponse, ResetResponse
from .grader import grade, calculate_quality_score

class DataCleaningEnv:
    """
    OpenEnv-compliant data cleaning environment.
    Reward system matched to Reasoning Gym (sparse + grade).
    """
    
    def __init__(self, task: str = "hard", data=None):
        self.task = task
        self.custom_data = data
        self.dataset: List[Dict[str, Any]] = []
        self.issues: List[Dict[str, Any]] = []
        self.done = False
        self.initial_issue_count = 0
        self.reset()

    def reset(self) -> ResetResponse:
        """Reset environment to initial state."""
        if self.custom_data is not None:
            self.dataset = [dict(row) for row in self.custom_data]
        else:
            self.dataset = generate_dirty_data(self.task)

        self.issues = detect_issues(self.dataset)
        self.initial_issue_count = len(self.issues)
        self.done = len(self.issues) == 0
        return ResetResponse(observation=self.state())

    def state(self) -> Observation:
        """Return current observation."""
        obs = Observation(
            data=[dict(row) for row in self.dataset],
            issues=[dict(issue) for issue in self.issues],
            echoed_message=None
        )
        # Add Reasoning Gym style score
        obs.score = grade(self.task, self.dataset)
        return obs

    def step(self, action: Action) -> StepResponse:
        """Apply action and return result (Reasoning Gym Style)."""
        ob = self.state()
        if self.done:
            return StepResponse(
                observation=ob,
                reward=0.0,
                done=True,
                info=Info(error="Environment already done")
            )

        act_str = action.action or action.message
        if not act_str:
            return StepResponse(observation=ob, reward=-0.1, done=self.done, info=Info(error="No action"))

        act_str = act_str.strip().lower()
        valid_actions = {"remove_duplicates", "fill_missing_age", "fix_email", "convert_age", "drop_invalid"}
        
        if act_str not in valid_actions:
            return StepResponse(observation=ob, reward=-0.1, done=self.done, info=Info(error=f"Unknown '{act_str}'"))

        error = None
        try:
            if act_str == "remove_duplicates": remove_duplicates(self.dataset)
            elif act_str == "fill_missing_age": fill_missing_age(self.dataset)
            elif act_str == "fix_email": fix_email(self.dataset)
            elif act_str == "convert_age": convert_age(self.dataset)
            elif act_str == "drop_invalid": drop_invalid(self.dataset)
        except Exception as exc:
            error = str(exc)

        self.issues = detect_issues(self.dataset)
        self.done = (len(self.issues) == 0)

        # Sparse reward like Reasoning Gym
        if self.done:
            reward = grade(self.task, self.dataset)
        elif error:
            reward = -0.1
        else:
            reward = 0.0

        reward = float(round(reward, 2))
        info = Info(error=error)
        
        return StepResponse(observation=self.state(), reward=reward, done=self.done, info=info)

    def calculate_score(self, rewards: List[float]) -> float:
        """Final session score based on absolute grade."""
        return grade(self.task, self.dataset)
    
    def get_quality_metrics(self, steps: int, rewards: List[float]) -> Dict[str, Any]:
        """Get comprehensive quality metrics."""
        score, metrics = calculate_quality_score(
            task=self.task,
            initial_issues=self.initial_issue_count,
            final_issues=len(self.issues),
            steps_taken=steps,
            rewards=rewards
        )
        return metrics

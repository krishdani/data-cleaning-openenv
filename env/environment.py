from typing import Any, Dict, List, Tuple
from .utils import generate_dirty_data, detect_issues
from .actions import remove_duplicates, fill_missing_age, fix_email, convert_age, drop_invalid
from .schemas import Observation, Action, Info, StepResponse, ResetResponse
from .grader import grade, calculate_quality_score

class DataCleaningEnv:
    """
    OpenEnv-compliant data cleaning environment.
    
    Agents interact via:
    - reset(task): Initialize environment for a task
    - step(action): Apply action and get reward
    - state(): Get current observation
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
        return Observation(
            data=[dict(row) for row in self.dataset],
            issues=[dict(issue) for issue in self.issues],
            echoed_message=None
        )

    def step(self, action: Action) -> StepResponse:
        """Apply action and return result."""
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
            return StepResponse(
                observation=ob,
                reward=-0.2,
                done=self.done,
                info=Info(error="No action provided")
            )

        # Extract primary action keyword
        act_str = act_str.strip().lower()

        valid_actions = {
            "remove_duplicates",
            "fill_missing_age",
            "fix_email",
            "convert_age",
            "drop_invalid",
        }
        
        if act_str not in valid_actions:
            return StepResponse(
                observation=ob,
                reward=-0.2,
                done=self.done,
                info=Info(error=f"Unknown action '{act_str}'")
            )

        previous_issue_count = len(self.issues)
        error = None

        try:
            if act_str == "remove_duplicates":
                remove_duplicates(self.dataset)
            elif act_str == "fill_missing_age":
                fill_missing_age(self.dataset)
            elif act_str == "fix_email":
                fix_email(self.dataset)
            elif act_str == "convert_age":
                convert_age(self.dataset)
            elif act_str == "drop_invalid":
                drop_invalid(self.dataset)
        except Exception as exc:
            error = str(exc)

        self.issues = detect_issues(self.dataset)
        new_issue_count = len(self.issues)

        if error is not None:
            reward = -0.2
        else:
            improvement = previous_issue_count - new_issue_count

            if new_issue_count == 0:
                reward = 1.0
            elif improvement > 0:
                reward = 0.7
            elif improvement == 0:
                reward = -0.3
            else:
                reward = -1.0

        reward = max(-1.0, min(1.0, reward))
        self.done = (len(self.issues) == 0)
        
        info = Info(error=error)
        return StepResponse(observation=self.state(), reward=reward, done=self.done, info=info)

    def calculate_score(self, rewards: List[float]) -> float:
        """
        Calculate final score based on accumulated rewards.
        
        Formula:
        - Base: sum of rewards / num steps
        - Bonus: Issue reduction percentage
        - Clamped: [0.0, 1.0]
        """
        if not rewards:
            return 0.001

        base_score = sum(rewards) / len(rewards)
        
        # Bonus for issue reduction
        if self.initial_issue_count > 0:
            issue_reduction = (self.initial_issue_count - len(self.issues)) / self.initial_issue_count
            bonus = issue_reduction * 0.3
        else:
            bonus = 0.0
        
        final_score = base_score * 0.7 + bonus
        return max(0.001, min(final_score, 0.999))
    
    def get_quality_metrics(self, steps: int, rewards: List[float]) -> Dict[str, Any]:
        """Get comprehensive quality metrics using grader."""
        score, metrics = calculate_quality_score(
            task=self.task,
            initial_issues=self.initial_issue_count,
            final_issues=len(self.issues),
            steps_taken=steps,
            rewards=rewards
        )
        return metrics
#!/usr/bin/env python3
import os
import sys
from typing import List
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from env import DataCleaningEnv, TASKS
from env.schemas import Action as MyEnvV4Action
from env.grader import safe_score

# ---------------------------------------------------------------------------
# CONFIG (Hackathon Guidelines Compliant)
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

MAX_STEPS = int(os.environ.get("MAX_STEPS", 10))
SUCCESS_SCORE_THRESHOLD = float(os.environ.get("SUCCESS_SCORE_THRESHOLD", 0.7))
MAX_TOTAL_REWARD = float(os.environ.get("MAX_TOTAL_REWARD", 15))

# Score must be strictly between 0 and 1 — never 0.0 or 1.0
SCORE_MIN = 0.01
SCORE_MAX = 0.99

# Initialize OpenAI client
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

# ---------------------------------------------------------------------------
# LOGGING (Hackathon Guidelines Format)
# ---------------------------------------------------------------------------
def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error=None):
    error_value = error if error is not None else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_value}",
        flush=True,
    )

def log_end(success, steps, rewards):
    reward_values = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={reward_values}",
        flush=True,
    )

# ---------------------------------------------------------------------------
# ENV WRAPPER
# ---------------------------------------------------------------------------
class EnvWrapper:
    def __init__(self, task: str):
        self._env = DataCleaningEnv(task=task)

    def reset(self):
        return self._env.reset()

    def step(self, action):
        return self._env.step(action)

    def close(self):
        pass

# ---------------------------------------------------------------------------
# VALID ACTIONS
# ---------------------------------------------------------------------------
VALID_ACTIONS = [
    "fix_email",
    "convert_age",
    "fill_missing_age",
    "remove_duplicates",
    "drop_invalid",
]

def fallback_action(step: int) -> str:
    return VALID_ACTIONS[(step - 1) % len(VALID_ACTIONS)]

# ---------------------------------------------------------------------------
# LLM CALL (OpenAI Client)
# ---------------------------------------------------------------------------
def get_action(step: int, history: List[str]) -> str:
    prompt = f"""You are a data cleaning agent. Choose the best cleaning action for this step.

Step: {step}
History: {history}

Available actions (return ONLY the action name, nothing else):
- fix_email
- convert_age
- fill_missing_age
- remove_duplicates
- drop_invalid

Return ONLY one action name."""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )

        action = response.choices[0].message.content.strip().lower()
        action = action.strip('"').strip("'").strip()

        if action in VALID_ACTIONS:
            return action

        for valid in VALID_ACTIONS:
            if valid in action:
                return valid

    except Exception:
        pass

    return fallback_action(step)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run_task(task_name: str):
    env = EnvWrapper(task=task_name)
    rewards = []
    steps_taken = 0
    success = False

    log_start(task_name, "DataCleaningEnv", MODEL_NAME)

    try:
        env.reset()

        for step in range(1, MAX_STEPS + 1):
            action_name = get_action(step, rewards)

            action_obj = MyEnvV4Action(action=action_name, message=action_name)

            step_response = env.step(action_obj)
            reward = float(step_response.reward or 0.0)
            done = bool(step_response.done)
            error = step_response.info.error if step_response.info else None
            
            rewards.append(reward)
            steps_taken = step
            log_step(step, action_name, reward, done, error)

            if done:
                break

        # Score calculation for internal success tracking
        total_reward = sum(rewards)
        raw_score = total_reward / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.5
        score = max(0.0, min(safe_score(raw_score), 1.0))
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        env.close()
        log_end(success, steps_taken, rewards)

def main():
    try:
        env_task = os.environ.get("TASK_NAME")
        if env_task and env_task in TASKS:
            tasks_to_run = [env_task]
        else:
            tasks_to_run = ["easy", "medium", "hard"]

        for task_name in tasks_to_run:
            run_task(task_name)
            
    except Exception as e:
        print(f"Global Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

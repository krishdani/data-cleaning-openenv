#!/usr/bin/env python3
import os
import asyncio
from typing import List
from dotenv import load_dotenv
load_dotenv()
from openai import AsyncOpenAI
from env import DataCleaningEnv, TASKS
from env.schemas import Action as MyEnvV4Action
from env.grader import safe_score

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TASK_NAME = os.environ.get("TASK_NAME", "hard")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4-turbo")
MAX_STEPS = int(os.environ.get("MAX_STEPS", 10))
SUCCESS_SCORE_THRESHOLD = float(os.environ.get("SUCCESS_SCORE_THRESHOLD", 0.7))
MAX_TOTAL_REWARD = float(os.environ.get("MAX_TOTAL_REWARD", 15))

# Score must be strictly between 0 and 1 — never 0.0 or 1.0
SCORE_MIN = 0.01
SCORE_MAX = 0.99

# ---------------------------------------------------------------------------
# LOGGING
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

def log_end(success, steps, score, rewards):
    reward_values = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={reward_values}",
        flush=True,
    )

# ---------------------------------------------------------------------------
# ENV WRAPPER
# ---------------------------------------------------------------------------
class AsyncEnvWrapper:
    def __init__(self, task: str):
        self._env = DataCleaningEnv(task=task)

    async def reset(self):
        return self._env.reset()

    async def step(self, action):
        return self._env.step(action)

    async def close(self):
        pass

# ---------------------------------------------------------------------------
# VALID ACTIONS — must match openenv.yaml action_schema enum exactly
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
# LLM CALL
# ---------------------------------------------------------------------------
async def get_action(client: AsyncOpenAI, step: int, history: List[str]) -> str:
    prompt = f"""You are a data cleaning agent. Choose the best cleaning action for this step.

Step: {step}
History: {history}

Available actions (return ONLY the action name, nothing else):
- fix_email         → fix invalid email addresses
- convert_age       → fix age fields with wrong data types
- fill_missing_age  → fill in missing age values
- remove_duplicates → remove duplicate rows
- drop_invalid      → drop rows that cannot be fixed

Return ONLY one action name from the list above."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )

        action = response.choices[0].message.content.strip().lower()

        # Clean up common LLM formatting issues
        action = action.strip('"').strip("'").strip()

        if action in VALID_ACTIONS:
            return action

        # Try partial match
        for valid in VALID_ACTIONS:
            if valid in action:
                return valid

    except Exception:
        pass

    return fallback_action(step)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
async def run_task(task_name: str, client: AsyncOpenAI):
    env = AsyncEnvWrapper(task=task_name)
    history = []
    rewards = []
    steps_taken = 0
    success = False
    score = SCORE_MIN  # default: never exactly 0.0

    log_start(task_name, "DataCleaningEnv", MODEL_NAME)

    try:
        await env.reset()

        for step in range(1, MAX_STEPS + 1):
            action_name = await get_action(client, step, history)

            # CRITICAL FIX: The action_schema requires "action" field, not just "message"
            # Pass the action as both the action field and message field
            action_obj = MyEnvV4Action(action=action_name, message=action_name)

            step_response = await env.step(action_obj)
            reward = float(step_response.reward or 0.0)
            done = bool(step_response.done)
            error = step_response.info.error if step_response.info else None
            rewards.append(reward)
            steps_taken = step
            log_step(step, action_name, reward, done, error)
            history.append(f"{action_name}:{reward:.2f}")

            if done:
                break

        # Compute score — clamp strictly to (0, 1)
        total_reward = sum(rewards)
        if MAX_TOTAL_REWARD and MAX_TOTAL_REWARD > 0:
            raw_score = total_reward / MAX_TOTAL_REWARD
        else:
            raw_score = 0.5  # safe default

        score = max(SCORE_MIN, min(safe_score(raw_score), SCORE_MAX))
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception:
        score = SCORE_MIN
    finally:
        await env.close()
        log_end(success, steps_taken, score, rewards)
        return {"task_id": task_name, "score": score}

async def main():
    api_key = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )
    try:
        env_task = os.environ.get("TASK_NAME")
        if env_task and env_task in TASKS:
            tasks_to_run = [env_task]
        else:
            # Run at least easy, medium, hard (platform requires >= 3 tasks)
            tasks_to_run = ["easy", "medium", "hard"]
            for t in TASKS:
                if t not in tasks_to_run:
                    tasks_to_run.append(t)

        results = []
        for task_name in tasks_to_run:
            res = await run_task(task_name, client)
            results.append(res)

        return results
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())

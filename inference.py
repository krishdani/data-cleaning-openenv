#!/usr/bin/env python3
import os
import json
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
load_dotenv()
from openai import AsyncOpenAI
from env import DataCleaningEnv, TASKS
from env.schemas import Action as MyEnvV4Action

# ---------------------------------------------------------------------------
# CONFIG (USES YOUR .env EXACTLY)
# ---------------------------------------------------------------------------
TASK_NAME = os.environ.get("TASK_NAME", "hard")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4-turbo")
MAX_STEPS = int(os.environ.get("MAX_STEPS", 10))
SUCCESS_SCORE_THRESHOLD = float(os.environ.get("SUCCESS_SCORE_THRESHOLD", 0.7))
MAX_TOTAL_REWARD = float(os.environ.get("MAX_TOTAL_REWARD", 15))

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
def log_start(task, env, model):
    print(f"[START] {json.dumps({'task': task, 'env': env, 'model': model})}", flush=True)

def log_step(step, action, reward, done, error=None):
    print(f"[STEP] {json.dumps({'step': step, 'action': action, 'reward': reward, 'done': done, 'error': error})}", flush=True)

def log_end(success, steps, score, rewards):
    print(f"[END] {json.dumps({'success': success, 'steps': steps, 'score': score, 'rewards': rewards})}", flush=True)

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
# SAFE ACTION LOGIC (VERY IMPORTANT FIX)
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
# LLM CALL (SAFE + NO CRASH)
# ---------------------------------------------------------------------------
async def get_action(client: AsyncOpenAI, step: int, history: List[str]) -> str:
    prompt = f"""
You are a data cleaning agent.

Step: {step}
History: {history}

Available actions:
- fix_email
- convert_age
- fill_missing_age
- remove_duplicates
- drop_invalid

Return ONLY one action name.
"""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )

        action = response.choices[0].message.content.strip().lower()

        if action in VALID_ACTIONS:
            return action

    except Exception as e:
        print(f"[DEBUG] API ERROR: {e}", flush=True)

    # fallback (CRITICAL to avoid crash)
    return fallback_action(step)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
async def main():
    api_key = os.environ.get("HF_TOKEN")  # using your env
    base_url = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )

    env = AsyncEnvWrapper(task=TASK_NAME)

    history = []
    rewards = []
    steps_taken = 0
    success = False
    score = 0.0

    log_start(TASK_NAME, "DataCleaningEnv", MODEL_NAME)

    try:
        state = await env.reset()

        for step in range(1, MAX_STEPS + 1):

            action = await get_action(client, step, history)

            state, reward, done, _ = await env.step(MyEnvV4Action(message=action))

            reward = reward or 0.0

            rewards.append(reward)
            steps_taken = step

            log_step(step, action, reward, done)

            history.append(f"{action}:{reward}")

            if done:
                break

        # ✅ FIXED SCORE LOGIC
        total_reward = sum(rewards)
        score = total_reward / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD else 0.0

        # clamp
        score = max(0.0, min(score, 1.0))

        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Runtime Error: {e}", flush=True)

    finally:
        await env.close()
        log_end(success, steps_taken, score, rewards)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
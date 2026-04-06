#!/usr/bin/env python3
"""
Baseline inference script for the Data Cleaning OpenEnv.
Matches the hackathon sample format.
"""
import os
import json
import asyncio
import time
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from env import DataCleaningEnv, TASKS
from env.schemas import Action as MyEnvV4Action

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TASK_NAME = os.environ.get("TASK_NAME", "hard")
BENCHMARK = "data-cleaning-openenv"
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-1.5-flash")
MAX_STEPS = 10
SUCCESS_SCORE_THRESHOLD = 0.7
MAX_TOTAL_REWARD = 5.0 # For normalization matching sample

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    entry = {"type": "START", "task": task, "env": env, "model": model}
    print(f"[START] {json.dumps(entry)}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    entry = {
        "type": "STEP",
        "step": step,
        "action": action,
        "reward": round(reward, 4),
        "done": done,
        "error": error
    }
    print(f"[STEP] {json.dumps(entry)}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    entry = {
        "type": "END",
        "success": success,
        "steps": steps,
        "score": round(score, 4),
        "rewards": [round(r, 4) for r in rewards]
    }
    print(f"[END] {json.dumps(entry)}", flush=True)

# ---------------------------------------------------------------------------
# Async Environment Wrapper (Local)
# ---------------------------------------------------------------------------

class AsyncEnvWrapper:
    def __init__(self, task: str):
        self._env = DataCleaningEnv(task=task)
    
    async def reset(self):
        return self._env.reset()
    
    async def step(self, action):
        return self._env.step(action)
    
    async def close(self):
        pass # Local env doesn't need cleanup

    @property
    def done(self):
        return self._env.done

# ---------------------------------------------------------------------------
# LLM Logic
# ---------------------------------------------------------------------------

async def get_model_message(client: AsyncOpenAI, step: int, last_echoed: Optional[str], last_reward: float, history: List[str]) -> str:
    """Choose the next cleaning action using LLM."""
    prompt = f"""You are a data cleaning agent.
Step {step}
Previous Reward: {last_reward}
History: {history}

Available actions:
- fix_email
- convert_age
- fill_missing_age
- remove_duplicates
- drop_invalid

Choose ONE action name. Respond with ONLY the name."""

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0
        )
        action = completion.choices[0].message.content.strip().lower()
        valid = {"fix_email", "convert_age", "fill_missing_age", "remove_duplicates", "drop_invalid"}
        if action in valid:
            return action
    except Exception:
        pass
    
    # Simple fallback sequence
    sequence = ["fix_email", "convert_age", "fill_missing_age", "remove_duplicates", "drop_invalid"]
    return sequence[(step-1) % len(sequence)]

# ---------------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------------

async def main():
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")
    base_url = os.environ.get("API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    
    client = AsyncOpenAI(api_key=api_key or "no-key", base_url=base_url)
    env = AsyncEnvWrapper(task=TASK_NAME)
    
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset() # OpenENV.reset()
        obs = result.observation
        last_echoed = obs.echoed_message
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            # Message/Action decision
            message = await get_model_message(client, step, last_echoed, last_reward, history)

            # Step in environment
            result = await env.step(MyEnvV4Action(message=message))
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            error = None

            rewards.append(reward)
            steps_taken = step
            last_echoed = obs.echoed_message
            last_reward = reward

            log_step(step=step, action=message, reward=reward, done=done, error=error)

            history.append(f"Step {step}: {message!r} -> reward {reward:+.2f}")

            if done:
                break

        # Score calculation matching sample logic
        # Sample uses sum(rewards) / MAX_TOTAL_REWARD
        score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0
        score = min(max(score, 0.0), 1.0)  # clamp to [0, 1]
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Runtime error: {e}", flush=True)
    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error (container cleanup): {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Pre-submission validation script for OpenEnv competition.
Checks environment compliance before submission.
"""

import os
import sys

def ok():
    return "[PASS]"

def fail():
    return "[FAIL]"

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_file(path: str, desc: str) -> bool:
    exists = os.path.isfile(path)
    print(f"  {ok() if exists else fail()} {desc}: {path}")
    return exists

def check_openenv_yaml() -> bool:
    try:
        import yaml
        with open("openenv.yaml", "r") as f:
            config = yaml.safe_load(f)
        required = ["name", "tasks", "action_schema", "observation_schema", "reward_range"]
        missing = [f for f in required if f not in config]
        if missing:
            print(f"  {fail()} openenv.yaml missing: {missing}")
            return False
        tasks = config.get("tasks", [])
        if not all(t in tasks for t in ["easy", "medium", "hard"]):
            print(f"  {fail()} openenv.yaml must have easy, medium, hard tasks")
            return False
        print(f"  {ok()} openenv.yaml valid (tasks: {tasks})")
        return True
    except Exception as e:
        print(f"  {fail()} openenv.yaml: {e}")
        return False

def check_env_package() -> bool:
    try:
        from env import DataCleaningEnv, TASKS, grade
        from env.schemas import Action, Observation, StepResponse, ResetResponse

        # Check tasks
        for t in ["easy", "medium", "hard"]:
            if t not in TASKS:
                print(f"  {fail()} Missing task: {t}")
                return False
        print(f"  {ok()} All 3 tasks defined")

        # Test reset/step/state cycle
        env = DataCleaningEnv(task="easy")
        reset_resp = env.reset()
        assert hasattr(reset_resp, "observation"), "reset() must return ResetResponse"
        print(f"  {ok()} reset() returns ResetResponse with observation")

        obs = env.state()
        assert hasattr(obs, "data") and hasattr(obs, "issues"), "state() must return Observation"
        print(f"  {ok()} state() returns Observation")

        action = Action(action="fill_missing_age")
        step_resp = env.step(action)
        assert hasattr(step_resp, "observation") and hasattr(step_resp, "reward") and hasattr(step_resp, "done"), \
            "step() must return StepResponse"
        assert -1.0 <= step_resp.reward <= 1.0, f"Reward {step_resp.reward} out of range"
        print(f"  {ok()} step() returns StepResponse (reward={step_resp.reward})")

        # Test graders
        for t in ["easy", "medium", "hard"]:
            g = grade(t, [{"name": "A", "age": 25, "email": "a@b.com"}])
            assert 0.0 <= g <= 1.0, f"Grade for {t} out of range: {g}"
        print(f"  {ok()} Graders return scores in [0.0, 1.0]")

        return True
    except Exception as e:
        print(f"  {fail()} Environment package error: {e}")
        return False

def check_api() -> bool:
    try:
        with open("api.py", "r", encoding="utf-8") as f:
            content = f.read()
        endpoints = {
            "/reset": 'POST /reset',
            "/step": 'POST /step',
            "/state": 'GET /state',
            "/health": 'GET /health',
        }
        all_ok = True
        for path, desc in endpoints.items():
            if path in content:
                print(f"  {ok()} {desc}")
            else:
                print(f"  {fail()} Missing {desc}")
                all_ok = False
        return all_ok
    except Exception as e:
        print(f"  {fail()} API check: {e}")
        return False

def check_inference() -> bool:
    try:
        with open("inference.py", "r", encoding="utf-8") as f:
            content = f.read()
        checks = [
            ("log_start", "[START] logging"),
            ("log_step", "[STEP] logging"),
            ("log_end", "[END] logging"),
            ("OPENAI_API_KEY", "OPENAI_API_KEY env var"),
            ("HF_TOKEN", "HF_TOKEN env var"),
        ]
        all_ok = True
        for pattern, desc in checks:
            if pattern in content:
                print(f"  {ok()} {desc}")
            else:
                print(f"  {fail()} Missing {desc}")
                all_ok = False
        return all_ok
    except Exception as e:
        print(f"  {fail()} Inference check: {e}")
        return False

def check_readme() -> bool:
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()
        sections = [
            ("Quick Start", "Setup instructions"),
            ("Environment Specification", "API specification"),
            ("Reward", "Reward system"),
            ("Tasks", "Task descriptions"),
            ("Deployment", "Deployment instructions"),
            ("Baseline", "Baseline scores"),
        ]
        all_ok = True
        for keyword, desc in sections:
            if keyword in content:
                print(f"  {ok()} {desc}")
            else:
                print(f"  {fail()} Missing: {desc}")
                all_ok = False
        return all_ok
    except Exception as e:
        print(f"  {fail()} README check: {e}")
        return False

def main():
    section("OpenEnv Pre-Submission Validation")

    all_passed = True

    section("1. File Structure")
    for path, desc in [
        ("openenv.yaml", "OpenEnv spec"),
        ("api.py", "FastAPI server"),
        ("inference.py", "Baseline inference"),
        ("Dockerfile", "Container config"),
        ("README.md", "Documentation"),
        ("requirements.txt", "Dependencies"),
        ("env/__init__.py", "Environment package"),
        ("env/schemas.py", "Pydantic models"),
        ("env/grader.py", "Grading system"),
    ]:
        if not check_file(path, desc):
            all_passed = False

    section("2. OpenEnv YAML")
    if not check_openenv_yaml():
        all_passed = False

    section("3. Environment Package")
    if not check_env_package():
        all_passed = False

    section("4. API Endpoints")
    if not check_api():
        all_passed = False

    section("5. Inference Script")
    if not check_inference():
        all_passed = False

    section("6. README")
    if not check_readme():
        all_passed = False

    section("RESULT")
    if all_passed:
        print(f"\n  {ok()} ALL CHECKS PASSED — Ready for submission!\n")
        return 0
    else:
        print(f"\n  {fail()} Some checks failed. Fix the issues above.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

---
title: Data Cleaning OpenEnv
emoji: 🧹
colorFrom: green
colorTo: teal
sdk: docker
tags:
  - openenv
---

# Data Cleaning OpenEnv

`data-cleaning-openenv` is a production-ready OpenEnv environment designed to train and evaluate AI agents on **real-world data cleaning tasks**. 

Instead of simple one-shot formatting, this environment teaches agents to handle the full lifecycle of data quality: detecting missing values, fixing malformed strings (emails), handling type mismatches, and removing duplicates step-by-step.

## Problem Statement

Most data cleaning benchmarks are static and don't reflect the iterative nature of data prep:

- They reward single-turn "clean everything" prompts instead of systematic debugging.
- They hide the intermediate states of the dataset from the agent.
- They don't provide granular rewards for partial progress (e.g., fixing 3 out of 5 issues).

This project closes that gap by turning data cleaning into a structured **RL-style environment** with an interactive dashboard and transparent scoring.

## Why This Matters

High-quality data is the fuel for all ML/AI. In production, automated data cleaning prevents:

- **Garbage In, Garbage Out**: Model performance drops due to noisy or missing inputs.
- **Pipeline Failures**: Crashes caused by unexpected types or null values.
- **Record Duplication**: Inefficient processing and incorrect reporting.

This environment is useful for:
- Benchmarking LLM reasoning on structured data.
- Training reinforcement learning agents on discrete tabular actions.
- Hackathon demos for AI-assisted data engineering.

## Environment Architecture

```text
User / AI Agent
        |
        v
Frontend (Next.js Dashboard)
  - Live dataset browser
  - Visual issue indicators
  - Real-time diagnostic logs
        |
        v
Python HTTP API (api.py)
  - /reset (Initialize task)
  - /step  (Apply cleaning action)
  - /state (Get current dataset)
        |
        v
DataCleaningEnv (env/environment.py)
  - Logic for data mutation
  - Issue detection (utils.py)
  - Task-specific loaders (tasks.py)
        |
        v
Grading System (env/grader.py)
  - Weighted reward shaping
  - Quality score normalization [0.0, 1.0]
```

## Reward System

Each episode is worth up to `1.0` total reward:

- `+1.0`  - All issues resolved (Episode success).
- `+0.7`  - Significant improvement (Multiple issues fixed).
- `-0.3`  - No improvement (Ineffective action).
- `-1.0`  - Dataset deteriorated (Created more issues).

The environment provides **reward shaping** across the trajectory, allowing agents to learn which actions deliver the most value for specific issue types.

## Scenario Library (Tasks)

The environment includes three standardized difficulty levels:

- **Easy**: 5-row dataset with basic missing values.
- **Medium**: 5-row dataset with format errors + missing values + type issues.
- **Hard**: 8-row dataset with duplicates, invalid formats, and complex mixed issues.

## Project Structure

```text
data-cleaning-openenv/
├── api.py              # FastAPI server (FastAPI + Pydantic)
├── inference.py        # Baseline async inference script (OpenAI Client)
├── openenv.yaml        # OpenEnv specification metadata
├── Dockerfile          # Multi-stage build (Next.js + Python)
├── validate.py         # Submissions validation script
├── env/                # Core Environment Logic
│   ├── environment.py  # Main OpenEnv class
│   ├── schemas.py      # Pydantic typed models
│   ├── actions.py      # Data mutation implementations
│   └── grader.py       # Scoring and metrics
└── frontend/           # Next.js 14 Dashboard UI
```

## Local Setup

### 1. Configure Environment
```bash
cp .env.example .env
# Add your OPENAI_API_KEY or HF_TOKEN
```

### 2. Run with Docker (Recommended)
```bash
docker build -t data-cleaning-env .
docker run -p 7860:7860 data-cleaning-env
```

### 3. Native Python Run
```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 7860
```

## Deployment to Hugging Face Spaces

1. Create a **Docker Space** on Hugging Face.
2. In the **Settings** tab, add your secrets:
    - `HF_TOKEN`: Your API key for evaluation.
    - `MODEL_NAME`: e.g., `gemini-1.5-flash`.
3. Push this repository to the Space. Use `main` branch.

## License

MIT

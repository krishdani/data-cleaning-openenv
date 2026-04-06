# Data Cleaning OpenEnv

A production-ready OpenEnv environment for training AI agents on **real-world data cleaning tasks**. Agents interact via the standard `step()` / `reset()` / `state()` API to detect and fix data quality issues across 3 difficulty levels.

## Environment Description

Data cleaning is a critical step in every ML pipeline. This environment simulates realistic data quality problems — missing values, malformed emails, type mismatches, and duplicate rows — and provides a structured RL-style interface for agents to learn effective cleaning strategies.

### Motivation

- Real-world task that data scientists face daily
- Clear, measurable success criteria
- Progressive difficulty for curriculum learning

## Quick Start

### Setup

```bash
pip install -r requirements.txt
```

### Run Baseline Inference

```bash
# Run all 3 tasks with deterministic baseline agent
python inference.py

# Run a single task
python inference.py easy

# Run with LLM agent (requires OPENAI_API_KEY)
OPENAI_API_KEY=sk-... python inference.py --use-llm hard
```

### Start the Environment Server

```bash
uvicorn api:app --host 0.0.0.0 --port 7860
```

### Start the Dashboard UI (Development)

```bash
cd frontend && npm install && npm run dev
```

## Environment Specification

### Action Space

| Action | Description |
|---|---|
| `fix_email` | Fix malformed email addresses (e.g., missing domain, special characters) |
| `convert_age` | Convert non-integer age values (strings, floats) to proper integers |
| `fill_missing_age` | Impute missing/null age values with the dataset median |
| `remove_duplicates` | Remove duplicate rows based on name+email+age fingerprint |
| `drop_invalid` | Drop rows that cannot be repaired (last resort) |

### Observation Space

```json
{
  "data": [{"name": "Alice", "age": 28, "email": "alice@example.com"}, ...],
  "issues": [{"row": 1, "type": "missing_age"}, {"row": 2, "type": "invalid_email"}, ...],
  "echoed_message": "optional agent message echo"
}
```

### Reward System

| Reward | Condition |
|---|---|
| `+1.0` | All issues resolved (episode complete) |
| `+0.7` | Significant improvement (issues reduced) |
| `-0.3` | No improvement (ineffective action) |
| `-1.0` | Dataset deteriorated (issues increased) |

Reward range: `[-1.0, +1.0]` — provides partial progress signals across the trajectory, not just binary end-of-episode feedback.

## Tasks

### Easy (Beginner)
- **Dataset**: 5 rows with 2 missing age values
- **Expected actions**: `fill_missing_age`
- **Baseline score**: ~0.85

### Medium (Intermediate)
- **Dataset**: 5 rows with format errors + missing values + type issues
- **Expected actions**: `fix_email`, `convert_age`, `fill_missing_age`
- **Baseline score**: ~0.72

### Hard (Advanced)
- **Dataset**: 8 rows with duplicates, invalid emails, wrong types, missing data, and shuffled order
- **Expected actions**: Full pipeline (`fix_email` → `convert_age` → `fill_missing_age` → `remove_duplicates` → `drop_invalid`)
- **Baseline score**: ~0.65

## Baseline Scores

```
Task       Score      Grade      Steps    Success
────────── ────────── ────────── ──────── ────────
easy       0.85+      0.80+      2-3      ✅
medium     0.70+      0.70+      4-5      ✅
hard       0.60+      0.75+      5-6      ✅
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reset` | Reset environment for a task. Body: `{"task": "easy"}` |
| `POST` | `/step` | Apply an action. Body: `{"action": "fix_email"}` |
| `GET` | `/state` | Get current observation |
| `GET` | `/health` | Health check |

## Deployment

### Docker

```bash
docker build -t data-cleaning-openenv .
docker run -p 7860:7860 data-cleaning-openenv
```

### Hugging Face Spaces

1. Push this repository to a GitHub repo
2. Create a new HF Space (Docker type)
3. Link to your GitHub repo
4. The Dockerfile exposes port 7860 (HF Spaces default)

## Project Structure

```
data-cleaning-openenv/
├── api.py              # FastAPI server with OpenEnv endpoints
├── inference.py        # Baseline inference script
├── environment.py      # Standalone environment (legacy)
├── openenv.yaml        # OpenEnv specification
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container for HF Spaces
├── validate.py         # Pre-submission validator
├── env/                # Core environment package
│   ├── environment.py  # OpenEnv-compliant environment class
│   ├── schemas.py      # Pydantic typed models (Action, Observation, etc.)
│   ├── actions.py      # Data cleaning action implementations
│   ├── grader.py       # Task-specific graders
│   ├── tasks.py        # Task definitions
│   └── utils.py        # Data generation & issue detection
└── frontend/           # Next.js dashboard UI
    └── src/
        ├── app/page.tsx
        ├── components/
        └── lib/api.ts
```

## License

MIT

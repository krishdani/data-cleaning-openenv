from typing import Dict

TASKS: Dict[str, Dict[str, str]] = {
    "easy": {
        "name": "easy",
        "description": "A small contact dataset with missing age values. The agent should recover missing ages using a simple imputation strategy.",
    },
    "medium": {
        "name": "medium",
        "description": "A contact dataset with missing ages, malformed emails, and inconsistent age types. The agent should fix formatting and normalize data.",
    },
    "hard": {
        "name": "hard",
        "description": "A noisy dataset with duplicates, invalid emails, wrong age types, and missing values. The agent should clean the dataset to a production-ready format.",
    },
}


def get_task(task_name: str) -> Dict[str, str]:
    return TASKS.get(task_name, TASKS["easy"])

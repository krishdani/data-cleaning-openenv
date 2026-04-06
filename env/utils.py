import copy
import re
from typing import List, Dict, Any
import numpy as np

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(email: Any) -> bool:
    return isinstance(email, str) and EMAIL_PATTERN.match(email) is not None


def _is_int_like(value: Any) -> bool:
    if isinstance(value, int):
        return True
    if isinstance(value, str) and value.isdigit():
        return True
    return False


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "name": row.get("name", "").strip().lower(),
        "email": row.get("email", "").strip().lower(),
        "age": row.get("age"),
    }
    return normalized


def generate_dirty_data(task: str) -> List[Dict[str, Any]]:
    base_rows = [
        {"name": "Alice Smith", "email": "alice.smith@example.com", "age": 28},
        {"name": "Carlos Diaz", "email": "carlos.diaz@example.com", "age": 34},
        {"name": "Fatima Khan", "email": "fatima.khan@example.com", "age": 22},
        {"name": "Jin Lee", "email": "jin.lee@example.com", "age": 41},
        {"name": "Mia Chen", "email": "mia.chen@example.com", "age": 30},
    ]

    rng = np.random.default_rng(42)
    data = copy.deepcopy(base_rows)

    if task == "easy":
        for idx in [1, 3]:
            data[idx]["age"] = None
        return data

    if task == "medium":
        data[0]["age"] = "29"
        data[1]["email"] = "carlos.diaz#example.com"
        data[2]["age"] = None
        data[3]["email"] = "jin.lee@example"
        data[4]["age"] = "thirty"
        return data

    if task == "hard":
        data[0]["age"] = None
        data[1]["email"] = "carlos.diaz@ example.com"
        data[2]["age"] = "26"
        data[3]["email"] = "jin.lee@example"
        data[4]["age"] = "forty-one"
        data.append(copy.deepcopy(data[2]))
        data.append({"name": "Alice Smith", "email": "alice.smith@example.com", "age": 28})
        data.append({"name": "Noah Brown", "email": "noah.brown@@example.com", "age": None})
        rng.shuffle(data)
        return data

    raise ValueError(f"Unknown task '{task}'. Choose easy, medium, or hard.")


def detect_issues(data: List[Dict[str, Any]], noise_tolerance: float = 0.0) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    seen = set()

    for index, row in enumerate(data):
        name = row.get("name")
        email = row.get("email")
        age = row.get("age")

        # Check for missing age with noise tolerance
        if age is None or age == "" or (isinstance(age, str) and not age.isdigit()):
            if np.random.random() > noise_tolerance:
                issues.append({"row": index, "type": "missing_age"})

        # Check for invalid email with noise tolerance
        if not _is_valid_email(email):
            if np.random.random() > noise_tolerance:
                issues.append({"row": index, "type": "invalid_email"})

        # Check for wrong type with noise tolerance
        if age is not None and not isinstance(age, int):
            if not _is_int_like(age):
                if np.random.random() > noise_tolerance:
                    issues.append({"row": index, "type": "wrong_type"})

        key = (str(name).strip().lower(), str(email).strip().lower(), str(age).strip() if isinstance(age, str) else age)
        if key in seen:
            if np.random.random() > noise_tolerance:
                issues.append({"row": index, "type": "duplicates"})
        else:
            seen.add(key)

    return issues


def summarize_state(data: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"data": copy.deepcopy(data), "issues": copy.deepcopy(issues)}

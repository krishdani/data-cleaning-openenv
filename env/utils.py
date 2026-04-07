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

    if task == "sprint":
        # Tricky edge cases: subtle typos, borderline values, swapped-looking data
        data = [
            {"name": "Liam O'Connor", "email": "liam.oconnor@mail.com", "age": 25},
            {"name": "Priya Sharma", "email": "priya.sharma@company", "age": "31"},
            {"name": "Tomáš Novák", "email": "tomas.novak@@mail.cz", "age": 29},
            {"name": "Emily Zhang", "email": "emily zhang@gmail.com", "age": None},
            {"name": "Ahmed Hassan", "email": "ahmed.hassan@domain.org", "age": "twenty-seven"},
            {"name": "Sofia Rossi", "email": "sofia.rossi#outlook.com", "age": 33},
            {"name": "Liam O'Connor", "email": "liam.oconnor@mail.com", "age": 25},  # duplicate
        ]
        rng.shuffle(data)
        return data

    if task == "nightmare":
        # Catastrophic corruption: mass duplicates, nulls, wrong types, bad emails
        data = [
            {"name": "Alex Rivera", "email": "alex.rivera@corp.com", "age": 28},
            {"name": "Alex Rivera", "email": "alex.rivera@corp.com", "age": 28},  # dup
            {"name": "Alex Rivera", "email": "alex.rivera@corp.com", "age": 28},  # dup
            {"name": "Morgan Lee", "email": "morgan.lee@", "age": None},
            {"name": "Jordan Kim", "email": "jordan.kim@@test.com", "age": "forty"},
            {"name": "Casey Brown", "email": "", "age": ""},
            {"name": "Taylor Swift", "email": "taylor#swift.com", "age": "19"},
            {"name": "Sam Wilson", "email": "sam wilson@mail.com", "age": None},
            {"name": "", "email": "ghost@void.com", "age": 0},
            {"name": "Dana White", "email": "dana.white@ufc", "age": "thirty-five"},
            {"name": "Morgan Lee", "email": "morgan.lee@", "age": None},  # dup
            {"name": "Robin Hood", "email": "robin.hood@sherwood.org", "age": -5},
        ]
        rng.shuffle(data)
        return data

    # Fallback for custom or unknown tasks
    return data


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

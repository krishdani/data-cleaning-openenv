from typing import List, Dict, Any
from .utils import _is_valid_email, _is_int_like

ACTIONS = [
    "remove_duplicates",
    "fill_missing_age",
    "fix_email",
    "convert_age",
    "drop_invalid",
]


def remove_duplicates(data: List[Dict[str, Any]]) -> None:
    seen = set()
    unique_rows: List[Dict[str, Any]] = []

    for row in data:
        key = (
            str(row.get("name", "")).strip().lower(),
            str(row.get("email", "")).strip().lower(),
            str(row.get("age", "")).strip(),
        )
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    data.clear()
    data.extend(unique_rows)


def fill_missing_age(data: List[Dict[str, Any]]) -> None:
    valid_ages = [row["age"] for row in data if isinstance(row.get("age"), int)]
    default_age = int(valid_ages[len(valid_ages) // 2]) if valid_ages else 30

    for row in data:
        age = row.get("age")
        if age is None or age == "":
            row["age"] = default_age
        elif isinstance(age, str) and age.isdigit():
            row["age"] = int(age)


def fix_email(data: List[Dict[str, Any]]) -> None:
    for row in data:
        email = row.get("email")
        name = row.get("name", "user").lower().replace(" ", ".")
        if email is None or not isinstance(email, str):
            row["email"] = f"{name}@example.com"
            continue

        cleaned = email.strip().replace(" ", "").replace("@@", "@").replace("#", "@")
        if "@" not in cleaned or "." not in cleaned.split("@")[1]:
            cleaned = f"{name}@example.com"

        row["email"] = cleaned


def convert_age(data: List[Dict[str, Any]]) -> None:
    for row in data:
        age = row.get("age")
        if isinstance(age, int):
            continue
        if isinstance(age, str) and age.isdigit():
            row["age"] = int(age)
        else:
            if isinstance(age, str) and age.lower().replace(" ", "").isdigit():
                row["age"] = int(age.lower().replace(" ", ""))
            else:
                row["age"] = None


def drop_invalid(data: List[Dict[str, Any]]) -> None:
    cleaned_rows: List[Dict[str, Any]] = []
    seen = set()

    for row in data:
        email = row.get("email")
        age = row.get("age")
        key = (
            str(row.get("name", "")).strip().lower(),
            str(email or "").strip().lower(),
            str(age or "").strip(),
        )

        if not _is_valid_email(email):
            continue
        if age is None or not isinstance(age, int):
            continue
        if "@" not in str(email or ""):
            continue
        if key in seen:
            continue

        seen.add(key)
        cleaned_rows.append(row)

    if len(cleaned_rows) > 0:
        data.clear()
        data.extend(cleaned_rows)

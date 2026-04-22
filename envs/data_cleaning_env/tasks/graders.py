import random
from typing import Dict, Any, List, Tuple


def generate_easy_dataset() -> List[Dict[str, Any]]:
    """Task 1: Missing values and wrong types only."""
    data = []
    for i in range(10):
        row = {
            "id": i,
            "age": random.choice([25, 30, None, 45, None, 22]),
            "salary": random.choice([50000, 60000, None, 75000, 80000]),
            "score": random.choice(["85", "90", "78", None, "88"]),
        }
        data.append(row)
    return data


def generate_medium_dataset() -> List[Dict[str, Any]]:
    """Task 2: Missing values + duplicates + formatting."""
    data = []
    base_rows = [
        {"id": 1, "name": "alice", "email": "ALICE@GMAIL.COM", "age": None},
        {"id": 2, "name": "Bob", "email": "bob@gmail.com", "age": 30},
        {"id": 3, "name": "charlie", "email": "charlie@gmail.com", "age": 25},
        {"id": 4, "name": "Bob", "email": "bob@gmail.com", "age": 30},
        {"id": 5, "name": None, "email": "dave@gmail.com", "age": 40},
        {"id": 6, "name": "eve", "email": "EVE@GMAIL.COM", "age": None},
        {"id": 7, "name": "charlie", "email": "charlie@gmail.com", "age": 25},
        {"id": 8, "name": "frank", "email": "frank@gmail.com", "age": 35},
    ]
    return base_rows


def generate_hard_dataset() -> List[Dict[str, Any]]:
    """Task 3: All issues combined + outliers + inconsistent categories."""
    data = [
        {"id": 1, "name": "alice", "dept": "Engineering", "salary": 75000, "age": None},
        {"id": 2, "name": None, "dept": "eng", "salary": 999999, "age": 28},
        {"id": 3, "name": "charlie", "dept": "HR", "salary": 65000, "age": 35},
        {"id": 4, "name": "dave", "dept": "h.r.", "salary": None, "age": 40},
        {"id": 5, "name": "alice", "dept": "Engineering", "salary": 75000, "age": None},
        {"id": 6, "name": "frank", "dept": "ENGINEERING", "salary": 80000, "age": 29},
        {"id": 7, "name": "grace", "dept": "Finance", "salary": -5000, "age": 32},
        {"id": 8, "name": "henry", "dept": "finance", "salary": 70000, "age": None},
    ]
    return data


def grade_easy(cleaned_data: List[Dict[str, Any]]) -> Tuple[float, str]:
    """Score Task 1: were missing values filled and types fixed?"""
    if not cleaned_data:
        return 0.0, "No data returned"

    total_checks = 0
    passed = 0

    for row in cleaned_data:
        # Check missing values filled
        for col in ["age", "salary", "score"]:
            total_checks += 1
            if row.get(col) is not None:
                passed += 1

        # Check score is numeric
        total_checks += 1
        try:
            float(row.get("score", ""))
            passed += 1
        except (ValueError, TypeError):
            pass

    score = round(passed / total_checks, 2) if total_checks > 0 else 0.0
    msg = f"Passed {passed}/{total_checks} checks"
    return score, msg


def grade_medium(cleaned_data: List[Dict[str, Any]]) -> Tuple[float, str]:
    """Score Task 2: duplicates removed, missing filled, emails lowercased."""
    if not cleaned_data:
        return 0.0, "No data returned"

    total_checks = 0
    passed = 0

    # Check no duplicates
    emails = [r.get("email", "").lower() for r in cleaned_data]
    total_checks += 1
    if len(emails) == len(set(emails)):
        passed += 1

    for row in cleaned_data:
        # Check missing name filled
        total_checks += 1
        if row.get("name") is not None:
            passed += 1

        # Check email is lowercase
        total_checks += 1
        email = row.get("email", "")
        if email == email.lower():
            passed += 1

        # Check missing age filled
        total_checks += 1
        if row.get("age") is not None:
            passed += 1

    score = round(passed / total_checks, 2) if total_checks > 0 else 0.0
    msg = f"Passed {passed}/{total_checks} checks"
    return score, msg


def grade_hard(cleaned_data: List[Dict[str, Any]]) -> Tuple[float, str]:
    """Score Task 3: all issues fixed."""
    if not cleaned_data:
        return 0.0, "No data returned"

    total_checks = 0
    passed = 0

    valid_depts = {"Engineering", "HR", "Finance"}
    salaries = [r.get("salary") for r in cleaned_data
                if r.get("salary") is not None]
    median_salary = sorted(salaries)[len(salaries)//2] if salaries else 70000

    # Check no duplicates
    names = [r.get("name") for r in cleaned_data]
    total_checks += 1
    if len(names) == len(set(names)):
        passed += 1

    for row in cleaned_data:
        # Check missing values filled
        for col in ["name", "age", "salary"]:
            total_checks += 1
            if row.get(col) is not None:
                passed += 1

        # Check dept standardized
        total_checks += 1
        if row.get("dept") in valid_depts:
            passed += 1

        # Check outlier salaries fixed
        total_checks += 1
        sal = row.get("salary", 0)
        if sal is not None and 0 < sal < 200000:
            passed += 1

    score = round(passed / total_checks, 2) if total_checks > 0 else 0.0
    msg = f"Passed {passed}/{total_checks} checks"
    return score, msg


TASKS = {
    "easy": {
        "name": "Fix Missing Values",
        "description": "Fill missing values and fix data types",
        "difficulty": "easy",
        "generate": generate_easy_dataset,
        "grade": grade_easy,
    },
    "medium": {
        "name": "Remove Duplicates and Fix Formatting",
        "description": "Remove duplicate rows and standardize formatting",
        "difficulty": "medium",
        "generate": generate_medium_dataset,
        "grade": grade_medium,
    },
    "hard": {
        "name": "Full Data Cleaning",
        "description": "Fix all issues: missing, duplicates, outliers, categories",
        "difficulty": "hard",
        "generate": generate_hard_dataset,
        "grade": grade_hard,
    },
}
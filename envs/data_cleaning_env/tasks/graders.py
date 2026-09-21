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


# IoT Streaming Task Generator and Grader
def generate_iot_stream_dataset(
    window_size: int = 24,
    corruption_type: str = "mixed",
    split: str = "train",
    seed: int = None,
) -> List[Dict[str, Any]]:
    """
    Task 4: IoT Air Quality Streaming Telemetry.
    Generates a contiguous time window of k hourly readings with realistic faults.
    """
    try:
        from data.iot_data_loader import UCIAirQualityLoader, SyntheticCorruptionInjector
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
        from data.iot_data_loader import UCIAirQualityLoader, SyntheticCorruptionInjector

    loader = UCIAirQualityLoader()
    train_df, test_df = loader.get_chronological_split(0.8)
    df = train_df if split == "train" else test_df

    injector = SyntheticCorruptionInjector(seed=seed)
    col = "CO(GT)"
    series_full = df[col].values

    # Select random contiguous window of length window_size
    max_start = max(0, len(series_full) - window_size)
    start_idx = random.randint(0, max_start) if seed is None else (seed % max_start)
    gt_window = series_full[start_idx : start_idx + window_size]

    corruption_res = injector.corrupt_window(gt_window, corruption_type=corruption_type)
    corrupted_window = corruption_res["corrupted"]
    masks = corruption_res["masks"]

    dataset = []
    for t in range(len(gt_window)):
        fault = "clean"
        for ftype, mask in masks.items():
            if mask[t]:
                fault = ftype
                break

        val = corrupted_window[t]
        # Handle nan / None
        sensor_val = None if (val is None or (isinstance(val, float) and np.isnan(val))) else float(val)

        row = {
            "id": t,
            "timestep": t,
            "sensor": col,
            "value": sensor_val,
            "raw_corrupted": sensor_val,
            "ground_truth": float(gt_window[t]),
            "fault_type": fault,
            "is_corrupted": fault != "clean",
        }
        dataset.append(row)

    return dataset


def grade_iot_stream(cleaned_data: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Score IoT streaming task by computing MAE & RMSE reduction vs pre-corruption ground truth.
    Returns (score, message). Score is bounded in [0.0, 1.0].
    """
    if not cleaned_data:
        return 0.0, "No cleaned data returned"

    errors_cleaned = []
    errors_corrupted = []

    for row in cleaned_data:
        gt = row.get("ground_truth")
        val = row.get("value")
        raw = row.get("raw_corrupted")

        if gt is None:
            continue

        # If agent left value as None or NaN, penalize by max deviation
        if val is None or (isinstance(val, float) and np.isnan(val)):
            val = 0.0

        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            raw = 0.0

        errors_cleaned.append(abs(float(val) - float(gt)))
        errors_corrupted.append(abs(float(raw) - float(gt)))

    if not errors_cleaned:
        return 0.0, "No valid ground truth comparisons found"

    mae_cleaned = float(np.mean(errors_cleaned))
    mae_corrupted = float(np.mean(errors_corrupted))
    rmse_cleaned = float(np.sqrt(np.mean([e ** 2 for e in errors_cleaned])))

    # Compute error reduction improvement
    if mae_corrupted < 1e-6:
        # Was already pristine
        score = 1.0 if mae_cleaned < 1e-6 else max(0.0, 1.0 - mae_cleaned)
    else:
        # Improvement ratio: 1.0 if mae_cleaned == 0, drops towards 0 if no improvement or worse
        improvement = (mae_corrupted - mae_cleaned) / mae_corrupted
        score = round(max(0.0, min(1.0, 0.5 + 0.5 * improvement)), 3)

    msg = (
        f"MAE: {mae_cleaned:.4f} (Raw: {mae_corrupted:.4f}), "
        f"RMSE: {rmse_cleaned:.4f}, Improvement: {(1.0 - mae_cleaned / max(mae_corrupted, 1e-6))*100:.1f}%"
    )
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
    "iot_stream": {
        "name": "IoT Sensor-Stream Denoising",
        "description": "Denoise sequential UCI Air Quality sensor stream (spikes, drift, dropouts, duplicates)",
        "difficulty": "streaming",
        "generate": generate_iot_stream_dataset,
        "grade": grade_iot_stream,
    },
}
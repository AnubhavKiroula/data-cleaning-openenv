import os
import requests
from openai import OpenAI

# ── Config ──────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
ENV_URL      = os.environ.get("ENV_URL", "http://localhost:8000")

client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

TASKS = ["easy", "medium", "hard"]


def ask_llm(observation: dict) -> dict:
    """Ask the LLM what cleaning action to take."""
    
    # Get first column as fallback
    columns = list(observation['current_data'].keys())
    first_column = columns[0] if columns else "id"
    
    prompt = f"""
You are a data cleaning agent. You receive a row of data and must clean it.

Current row data: {observation['current_data']}
Issues detected: {observation['issues_detected']}
Legal actions: {observation['legal_actions']}
Available columns: {columns}

Choose ONE action from the legal actions list.
Respond in this exact JSON format with ALL three fields always present:
{{
  "action_type": "fill_missing",
  "column": "age",
  "value": 30
}}

Rules:
- action_type must be from legal_actions list
- column must ALWAYS be one of: {columns}
- value is required for fill_missing, optional for others (use null if not needed)
- For fill_missing: provide a sensible default value
- For skip: still include column field using first available column
- ALWAYS include all three fields: action_type, column, value
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    import json
    text = response.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(text)
    
    # Safety fallbacks
    if "column" not in parsed or not parsed["column"]:
        parsed["column"] = first_column
    if "value" not in parsed:
        parsed["value"] = None
    if parsed.get("column") not in columns:
        parsed["column"] = first_column
        
    return parsed


def run_task(task_name: str) -> float:
    """Run one full episode for a task and return score."""
    print(f"\n{'='*50}")
    print(f"Running task: {task_name.upper()}")
    print(f"{'='*50}")

    # Reset
    obs = requests.post(
        f"{ENV_URL}/reset",
        json={"task_name": task_name}
    ).json()

    step = 0
    while not obs["done"]:
        step += 1
        print(f"  Row {obs['current_row']+1}/{obs['total_rows']} | "
              f"Issues: {obs['issues_detected']}")

        try:
            action = ask_llm(obs)
            print(f"  Action: {action}")
        except Exception as e:
            print(f"  LLM error: {e} — using skip")
            action = {
                "action_type": "skip",
                "column": list(obs["current_data"].keys())[0],
                "value": None
            }

        obs = requests.post(
            f"{ENV_URL}/step",
            json=action
        ).json()
        print(f"  Reward: {obs['reward']:.3f}")

    # Get final score
    state = requests.get(f"{ENV_URL}/state").json()
    score = state["score"]
    total_reward = state["total_reward"]

    print(f"\n  Final Score:  {score:.2f}")
    print(f"  Total Reward: {total_reward:.3f}")
    print(f"  Steps taken:  {step}")
    return score


def main():
    print("Data Cleaning OpenEnv — Baseline Inference")
    print("Model:", MODEL_NAME)
    print("Env:  ", ENV_URL)

    # Health check
    try:
        health = requests.get(f"{ENV_URL}/health").json()
        print("Server:", health)
    except Exception:
        print("ERROR: Server not running at", ENV_URL)
        return

    scores = {}
    for task in TASKS:
        scores[task] = run_task(task)

    print(f"\n{'='*50}")
    print("BASELINE RESULTS")
    print(f"{'='*50}")
    for task, score in scores.items():
        print(f"  {task:10s}: {score:.2f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  {'average':10s}: {avg:.2f}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
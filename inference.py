import os
import requests
from openai import OpenAI
from typing import List, Optional

# Load .env file if present (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required in production

# ── Config ──────────────────────────────────────────────────────────────
# Mandatory environment variables per hackathon requirements
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")  # Default to local env
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")                # Default model
HF_TOKEN = os.getenv("HF_TOKEN")                                    # No default - required

# OpenAI client configured with environment variables
client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
BENCHMARK = "data-cleaning-env"
TASKS = ["easy", "medium", "hard"]


# ── Structured Logging Functions (MANDATORY FORMAT) ─────────────────────
def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] line at episode begin."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    """Emit [STEP] line after each env.step() with exact format."""
    error_val = error if error else "null"
    done_val = str(done).lower()  # Must be lowercase: true/false
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Emit [END] line after episode completes. Always called even on exception."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    success_val = str(success).lower()  # Must be lowercase: true/false
    print(
        f"[END] success={success_val} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


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
    """Run one full episode for a task and return score in [0, 1] range."""
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    
    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
    
    try:
        # Reset environment
        obs = requests.post(
            f"{ENV_URL}/reset",
            json={"task_name": task_name}
        ).json()

        # Run episode until done
        while not obs["done"]:
            steps_taken += 1
            
            # Get action from LLM
            error_msg = None
            try:
                action = ask_llm(obs)
                action_str = f"{action['action_type']}('{action['column']}',{action['value']})"
            except Exception as e:
                error_msg = str(e)
                # Fallback action on LLM error
                action = {
                    "action_type": "skip",
                    "column": list(obs["current_data"].keys())[0] if obs["current_data"] else "id",
                    "value": None
                }
                action_str = f"skip('{action['column']}',null)"

            # Take step in environment
            try:
                obs = requests.post(
                    f"{ENV_URL}/step",
                    json=action
                ).json()
                reward = obs.get("reward", 0.0)
                done = obs.get("done", False)
            except Exception as e:
                error_msg = str(e)
                reward = 0.0
                done = True
                obs = {"done": True, "reward": 0.0}
            
            rewards.append(reward)
            log_step(step=steps_taken, action=action_str, reward=reward, done=done, error=error_msg)
            
            if done:
                break

        # Get final score from environment grader (must be in [0, 1])
        try:
            state = requests.get(f"{ENV_URL}/state").json()
            score = state.get("score", 0.0)
            # Clamp score to [0, 1] range as required
            score = min(max(score, 0.0), 1.0)
            # Success if score meets reasonable threshold
            success = score >= 0.5
        except Exception as e:
            score = 0.0
            success = False

    except Exception as e:
        # Even on exception, we must emit [END]
        pass
    
    finally:
        # Always emit [END] line, even on exception
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    
    return score


def main():
    """Main inference script entry point."""
    # Health check - verify server is running
    try:
        health = requests.get(f"{ENV_URL}/health", timeout=5).json()
        if health.get("status") != "ok":
            print(f"[ERROR] Server not healthy at {ENV_URL}", flush=True)
            return
    except Exception as e:
        print(f"[ERROR] Server not running at {ENV_URL}: {e}", flush=True)
        return

    # Run inference on all tasks
    scores = {}
    for task in TASKS:
        scores[task] = run_task(task)

    # Print summary (not part of structured output, just for convenience)
    print(f"\n{'='*60}", flush=True)
    print("BASELINE RESULTS SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    for task, score in scores.items():
        print(f"  {task:10s}: {score:.3f}", flush=True)
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    print(f"  {'average':10s}: {avg:.3f}", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
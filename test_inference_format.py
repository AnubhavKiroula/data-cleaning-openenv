"""
Test version of inference.py that uses rule-based actions (no LLM)
to verify the structured logging format matches requirements exactly.
"""
import os
import requests
from typing import List, Optional

ENV_URL = "http://localhost:7860"
BENCHMARK = "data-cleaning-env"
MODEL_NAME = "rule-based-test"
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


def get_rule_based_action(obs: dict) -> dict:
    """Rule-based action selection (no LLM needed for testing)."""
    issues = obs["issues_detected"]
    legal = obs["legal_actions"]
    data = obs["current_data"]
    first_col = list(data.keys())[0] if data else "id"
    
    # Default
    action = {"action_type": "skip", "column": first_col, "value": None}
    
    if "missing:age" in issues and "fill_missing" in legal:
        action = {"action_type": "fill_missing", "column": "age", "value": 30}
    elif "missing:salary" in issues and "fill_missing" in legal:
        action = {"action_type": "fill_missing", "column": "salary", "value": 60000}
    elif "missing:score" in issues and "fill_missing" in legal:
        action = {"action_type": "fill_missing", "column": "score", "value": 80}
    elif "missing:name" in issues and "fill_missing" in legal:
        action = {"action_type": "fill_missing", "column": "name", "value": "unknown"}
    elif "wrong_type:score" in issues and "fix_type" in legal:
        action = {"action_type": "fix_type", "column": "score", "value": None}
    elif "formatting:email" in issues and "fix_formatting" in legal:
        action = {"action_type": "fix_formatting", "column": "email", "value": None}
    elif "formatting:name" in issues and "fix_formatting" in legal:
        action = {"action_type": "fix_formatting", "column": "name", "value": None}
    elif "formatting:dept" in issues and "fix_category" in legal:
        action = {"action_type": "fix_category", "column": "dept", "value": None}
    
    return action


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
            
            # Get action (rule-based, no LLM)
            error_msg = None
            try:
                action = get_rule_based_action(obs)
                action_str = f"{action['action_type']}('{action['column']}',{action['value']})"
            except Exception as e:
                error_msg = str(e)
                # Fallback action on error
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

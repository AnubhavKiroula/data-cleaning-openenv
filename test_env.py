import requests

base = "http://localhost:8000"

def run_task(task_name):
    print(f"\n{'='*50}")
    print(f"TASK: {task_name.upper()}")
    print(f"{'='*50}")

    # Reset
    obs = requests.post(f"{base}/reset", json={"task_name": task_name}).json()
    print(f"Total rows: {obs['total_rows']}")

    while not obs["done"]:
        print(f"\n  Row {obs['current_row']+1} | Data: {obs['current_data']}")
        print(f"  Issues: {obs['issues_detected']}")
        print(f"  Legal actions: {obs['legal_actions']}")

        # Simple rule-based agent
        action = {"action_type": "skip", "column": list(obs["current_data"].keys())[0], "value": None}

        if "missing:age" in obs["issues_detected"]:
            action = {"action_type": "fill_missing", "column": "age", "value": 30}
        elif "missing:salary" in obs["issues_detected"]:
            action = {"action_type": "fill_missing", "column": "salary", "value": 60000}
        elif "missing:name" in obs["issues_detected"]:
            action = {"action_type": "fill_missing", "column": "name", "value": "unknown"}
        elif "wrong_type:score" in obs["issues_detected"]:
            action = {"action_type": "fix_type", "column": "score", "value": None}
        elif "formatting:email" in obs["issues_detected"]:
            action = {"action_type": "fix_formatting", "column": "email", "value": None}

        obs = requests.post(f"{base}/step", json=action).json()
        print(f"  Action: {action['action_type']} | Reward: {obs['reward']}")

    state = requests.get(f"{base}/state").json()
    print(f"\n  Final Score:  {state['score']}")
    print(f"  Total Reward: {state['total_reward']}")
    return state["score"]

# Run all 3 tasks
scores = {}
for task in ["easy", "medium", "hard"]:
    scores[task] = run_task(task)

print(f"\n{'='*50}")
print("FINAL SCORES")
print(f"{'='*50}")
for task, score in scores.items():
    print(f"  {task:10s}: {score:.2f}")
print(f"  average   : {sum(scores.values())/len(scores):.2f}")
import requests

base = "http://localhost:7860"

def run_task(task_name):
    print(f"\n{'='*50}")
    print(f"TASK: {task_name.upper()}")
    print(f"{'='*50}")

    obs = requests.post(f"{base}/reset", json={"task_name": task_name}).json()
    print(f"Total rows: {obs['total_rows']}")

    while not obs["done"]:
        print(f"\n  Row {obs['current_row']+1} | Data: {obs['current_data']}")
        print(f"  Issues: {obs['issues_detected']}")
        print(f"  Legal actions: {obs['legal_actions']}")

        issues = obs["issues_detected"]
        legal  = obs["legal_actions"]
        data   = obs["current_data"]
        first_col = list(data.keys())[0]

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

        response = requests.post(f"{base}/step", json=action)
        if response.status_code != 200 or not response.text:
            print(f"  ERROR: server returned {response.status_code} — {response.text}")
            break

        obs = response.json()
        print(f"  Action: {action['action_type']} | Reward: {obs['reward']}")

    state = requests.get(f"{base}/state").json()
    print(f"\n  Final Score:  {state['score']}")
    print(f"  Total Reward: {state['total_reward']}")
    return state["score"]

scores = {}
for task in ["easy", "medium", "hard"]:
    scores[task] = run_task(task)

print(f"\n{'='*50}")
print("FINAL SCORES")
print(f"{'='*50}")
for task, score in scores.items():
    print(f"  {task:10s}: {score:.2f}")
print(f"  average   : {sum(scores.values())/len(scores):.2f}")
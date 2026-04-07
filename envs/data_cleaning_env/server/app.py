import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Any, Optional

try:
    from server.environment import DataCleaningEnvironment
except ModuleNotFoundError:
    from environment import DataCleaningEnvironment

app = FastAPI(
    title="Data Cleaning OpenEnv",
    description="A real-world data cleaning RL environment.",
    version="1.0.0",
)

# ✅ Single shared instance — persists across requests
env = DataCleaningEnvironment()


class ResetRequest(BaseModel):
    task_name: str = "easy"


class StepRequest(BaseModel):
    action_type: str
    column: str
    value: Optional[Any] = None


@app.post("/reset")
def reset(request: Optional[ResetRequest] = None):
    try:
        task_name = request.task_name if request else "easy"
        return env.reset(task_name=task_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
def step(request: StepRequest):
    try:
        return env.step(
            action_type=request.action_type,
            column=request.column,
            value=request.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
def state():
    return env.get_state()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    try:
        from tasks.graders import TASKS
    except ModuleNotFoundError:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from tasks.graders import TASKS
    return {
        k: {
            "name": v["name"],
            "description": v["description"],
            "difficulty": v["difficulty"],
        }
        for k, v in TASKS.items()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_env = DataCleaningEnvironment()  # isolated per connection
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            if msg_type == "reset":
                try:
                    result = ws_env.reset(task_name=message.get("task_name", "easy"))
                    await websocket.send_json({"status": "ok", **result})
                except ValueError as e:
                    await websocket.send_json({"status": "error", "detail": str(e)})
            elif msg_type == "step":
                try:
                    result = ws_env.step(
                        action_type=message.get("action_type"),
                        column=message.get("column"),
                        value=message.get("value"),
                    )
                    await websocket.send_json({"status": "ok", **result})
                except ValueError as e:
                    await websocket.send_json({"status": "error", "detail": str(e)})
            elif msg_type == "state":
                await websocket.send_json({"status": "ok", **ws_env.get_state()})
            elif msg_type == "health":
                await websocket.send_json({"status": "ok", "message": "healthy"})
            else:
                await websocket.send_json({"status": "error", "detail": f"Unknown type: {msg_type}"})
    except WebSocketDisconnect:
        pass
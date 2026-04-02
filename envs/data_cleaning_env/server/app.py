import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Any, Optional
from server.environment import DataCleaningEnvironment

app = FastAPI(
    title="Data Cleaning OpenEnv",
    description="A real-world data cleaning RL environment following the OpenEnv spec.",
    version="1.0.0",
)


class ResetRequest(BaseModel):
    task_name: str = "easy"


class StepRequest(BaseModel):
    action_type: str
    column: str
    value: Optional[Any] = None


# ------------------------------------------------------------------ #
#  HTTP endpoints (stateless)                                          #
# ------------------------------------------------------------------ #

@app.post("/reset")
def reset(request: ResetRequest):
    try:
        env = DataCleaningEnvironment()
        return env.reset(task_name=request.task_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
def step(request: StepRequest):
    try:
        env = DataCleaningEnvironment()
        return env.step(
            action_type=request.action_type,
            column=request.column,
            value=request.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
def state():
    env = DataCleaningEnvironment()
    return env.get_state()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    from tasks.graders import TASKS
    return {
        k: {
            "name": v["name"],
            "description": v["description"],
            "difficulty": v["difficulty"],
        }
        for k, v in TASKS.items()
    }


# ------------------------------------------------------------------ #
#  WebSocket endpoint — persistent session (OpenEnv spec)             #
# ------------------------------------------------------------------ #

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Persistent WebSocket session for efficient RL training.
    Each connection gets its own isolated environment instance.

    Message format (client → server):
        {"type": "reset", "task_name": "easy"}
        {"type": "step", "action_type": "fill_missing", "column": "age", "value": 30}
        {"type": "state"}
        {"type": "health"}

    Response format (server → client):
        Standard observation/state dict with added "status": "ok"
    """
    await websocket.accept()
    env = DataCleaningEnvironment()  # Isolated instance per connection

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "reset":
                task_name = message.get("task_name", "easy")
                try:
                    result = env.reset(task_name=task_name)
                    await websocket.send_json({"status": "ok", **result})
                except ValueError as e:
                    await websocket.send_json({"status": "error", "detail": str(e)})

            elif msg_type == "step":
                try:
                    result = env.step(
                        action_type=message.get("action_type"),
                        column=message.get("column"),
                        value=message.get("value"),
                    )
                    await websocket.send_json({"status": "ok", **result})
                except ValueError as e:
                    await websocket.send_json({"status": "error", "detail": str(e)})

            elif msg_type == "state":
                result = env.get_state()
                await websocket.send_json({"status": "ok", **result})

            elif msg_type == "health":
                await websocket.send_json({"status": "ok", "message": "healthy"})

            else:
                await websocket.send_json({
                    "status": "error",
                    "detail": f"Unknown message type: {msg_type}. Use reset/step/state/health."
                })

    except WebSocketDisconnect:
        pass  # Client disconnected cleanly — environment instance is garbage collected
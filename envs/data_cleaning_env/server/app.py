from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from server.environment import DataCleaningEnvironment

app = FastAPI(title="Data Cleaning OpenEnv")
env = DataCleaningEnvironment()


class ResetRequest(BaseModel):
    task_name: str = "easy"


class StepRequest(BaseModel):
    action_type: str
    column: str
    value: Optional[Any] = None


@app.post("/reset")
def reset(request: ResetRequest):
    try:
        return env.reset(task_name=request.task_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
def step(request: StepRequest):
    try:
        return env.step(
            action_type=request.action_type,
            column=request.column,
            value=request.value
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
    from tasks.graders import TASKS
    return {
        k: {
            "name": v["name"],
            "description": v["description"],
            "difficulty": v["difficulty"]
        }
        for k, v in TASKS.items()
    }
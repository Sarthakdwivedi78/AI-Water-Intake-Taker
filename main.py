from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from backend.database import (
        log_water, get_today_total, get_history, get_all_logs,
        get_user_target, set_user_target,
    )
    from backend.agent import get_ai_feedback
except ImportError:
    from database import (
        log_water, get_today_total, get_history, get_all_logs,
        get_user_target, set_user_target,
    )
    from agent import get_ai_feedback

app = FastAPI(title="💧 Water Intake AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ───────────────────────────────────────────────────────────

class LogRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    amount_ml: int = Field(gt=0, le=10000)


class UserRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)


class TargetRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    daily_target_ml: int = Field(gt=100, le=20000)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "💧 Water Intake AI Agent is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/log")
def log_intake(req: LogRequest):
    """Log water intake. Returns total today + user's target + AI feedback."""
    try:
        total_today = log_water(req.user_id, req.amount_ml)
        target = get_user_target(req.user_id)
        ai_feedback = get_ai_feedback(req.user_id, req.amount_ml, total_today, target)
        return {
            "user_id": req.user_id,
            "logged_ml": req.amount_ml,
            "total_today_ml": total_today,
            "daily_target_ml": target,
            "ai_feedback": ai_feedback,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/today")
def today_total(req: UserRequest):
    """Get today's total and target for a user."""
    total = get_today_total(req.user_id)
    target = get_user_target(req.user_id)
    return {
        "user_id": req.user_id,
        "total_today_ml": total,
        "daily_target_ml": target,
    }


@app.post("/history")
def history(req: UserRequest):
    """Get full daily history for a user."""
    data = get_history(req.user_id)
    target = get_user_target(req.user_id)
    return {
        "user_id": req.user_id,
        "daily_target_ml": target,
        "history": data,
    }


@app.post("/set-target")
def set_target(req: TargetRequest):
    """Set or update the user's daily water target."""
    try:
        saved = set_user_target(req.user_id, req.daily_target_ml)
        return {
            "user_id": req.user_id,
            "daily_target_ml": saved,
            "message": f"Daily target updated to {saved} ml ✅",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-target")
def get_target(req: UserRequest):
    """Get the user's current daily target."""
    target = get_user_target(req.user_id)
    return {"user_id": req.user_id, "daily_target_ml": target}

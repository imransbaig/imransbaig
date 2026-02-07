"""Router for the agentic coach engine -- runs the full SENSE->INFER->PLAN->ACT loop."""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.brain.coach_engine import CoachEngine
from app.signals.feature_extractor import SensorData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coach", tags=["coach"])

# Singleton engine instance
_engine = CoachEngine()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CoachProcessRequest(BaseModel):
    user_id: str = "demo_user"
    mode: str = "passive"


class CoachProcessResponse(BaseModel):
    inferred_state: dict
    next_action: Optional[dict] = None
    reason_trace: Optional[dict] = None
    trend_summary: Optional[dict] = None
    action_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    action_id: str
    helpful: bool
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers -- generate realistic simulated sensor data
# ---------------------------------------------------------------------------

def _generate_demo_readings() -> list[SensorData]:
    """Generate a realistic batch of simulated sensor readings."""
    now = datetime.utcnow()
    readings: list[SensorData] = []

    # Heart rate readings (last 30 minutes, every 2 minutes)
    base_hr = random.choice([65, 72, 78, 85, 92])  # varies per call
    for i in range(15):
        ts = now - timedelta(minutes=30 - i * 2)
        hr = base_hr + random.uniform(-8, 12)
        readings.append(SensorData(
            reading_type="heart_rate",
            value=round(hr, 1),
            timestamp=ts,
            metadata={"source": "simulated"},
        ))

    # Sleep readings (from last night)
    sleep_start = now.replace(hour=23, minute=0, second=0) - timedelta(days=1)
    sleep_quality = random.choice(["good", "fair", "poor"])
    sleep_hours = {"good": 7.5, "fair": 6.0, "poor": 4.5}[sleep_quality]
    for i in range(int(sleep_hours * 2)):
        ts = sleep_start + timedelta(minutes=i * 30)
        stage = random.choice(["light", "deep", "rem", "awake"])
        readings.append(SensorData(
            reading_type="sleep",
            value={"light": 1, "deep": 2, "rem": 3, "awake": 0}[stage],
            timestamp=ts,
            metadata={"stage": stage, "source": "simulated"},
        ))

    # Step/activity readings (today)
    for i in range(12):
        ts = now - timedelta(hours=12 - i)
        steps = random.randint(0, 800)
        readings.append(SensorData(
            reading_type="steps",
            value=float(steps),
            timestamp=ts,
            metadata={"source": "simulated"},
        ))

    return readings


def _generate_demo_cues() -> list[SensorData]:
    """Optionally generate a user cue."""
    now = datetime.utcnow()
    cues = []
    if random.random() < 0.4:
        cue_type = random.choice(["stress", "mood_low", "pain"])
        cues.append(SensorData(
            reading_type="cue",
            value=1.0,
            timestamp=now - timedelta(minutes=random.randint(5, 45)),
            metadata={"cue_type": cue_type},
        ))
    return cues


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/process", response_model=CoachProcessResponse)
def process_cycle(req: CoachProcessRequest) -> CoachProcessResponse:
    """Run one full agentic cycle with simulated sensor data."""
    readings = _generate_demo_readings()
    cues = _generate_demo_cues()

    result = _engine.process(
        user_id=req.user_id,
        readings=readings,
        cues=cues,
        mode=req.mode,
    )

    return CoachProcessResponse(**result.to_dict())


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest) -> dict:
    """Record user feedback for a delivered action."""
    success = _engine.record_feedback(
        action_id=req.action_id,
        helpful=req.helpful,
        note=req.note,
    )
    return {"recorded": success}


@router.post("/reset")
def reset_user(user_id: str = "demo_user") -> dict:
    """Clear in-memory history for a user (fresh start)."""
    _engine.clear_history(user_id)
    return {"reset": True, "user_id": user_id}

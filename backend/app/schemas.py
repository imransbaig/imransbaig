"""Pydantic schemas for request validation and response serialization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import CueType, ReadingType, StateType


# ---------------------------------------------------------------------------
# Reason Trace
# ---------------------------------------------------------------------------

class ReasonTrace(BaseModel):
    """Provenance record explaining why an action was recommended.

    Captures the full chain from trigger signal through inference to
    the final action, enabling transparency and debugging.
    """

    trace_id: str
    timestamp: datetime
    trigger: str
    signals: dict
    inference: str
    action: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Sensor Reading Schemas
# ---------------------------------------------------------------------------

class SensorReadingCreate(BaseModel):
    """Schema for creating a single sensor reading."""

    user_id: int
    timestamp: Optional[datetime] = None
    reading_type: ReadingType
    value: float
    metadata: Optional[dict] = None


class SensorReadingResponse(BaseModel):
    """Schema returned when reading a sensor data point."""

    id: int
    user_id: int
    timestamp: datetime
    reading_type: ReadingType
    value: float
    reading_metadata: Optional[dict] = Field(None, alias="metadata", serialization_alias="metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}


class SyncRequest(BaseModel):
    """Batch request to ingest multiple sensor readings at once."""

    readings: list[SensorReadingCreate]


class SyncResponse(BaseModel):
    """Response after a batch sync, indicating how many readings were stored."""

    count: int
    message: str = "Readings synced successfully"


# ---------------------------------------------------------------------------
# Inferred State Schemas
# ---------------------------------------------------------------------------

class InferredStateResponse(BaseModel):
    """The latest inferred state for a user."""

    id: int
    user_id: int
    timestamp: datetime
    state_type: StateType
    confidence: float
    signals: Optional[dict] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Action Schemas
# ---------------------------------------------------------------------------

class ActionResponse(BaseModel):
    """An action recommendation with its reason trace."""

    id: int
    user_id: int
    timestamp: datetime
    action_type: str
    reason_trace: Optional[dict] = None
    delivered: bool
    dismissed: bool

    model_config = {"from_attributes": True}


class ActionDeliverResponse(BaseModel):
    """Confirmation that an action has been marked as delivered."""

    id: int
    delivered: bool
    message: str = "Action marked as delivered"


# ---------------------------------------------------------------------------
# Cue Schemas
# ---------------------------------------------------------------------------

class CueCreate(BaseModel):
    """Schema for logging a user-reported cue."""

    user_id: int
    cue_type: CueType
    note: Optional[str] = None


class CueResponse(BaseModel):
    """Schema returned after a cue is logged."""

    id: int
    user_id: int
    timestamp: datetime
    cue_type: CueType
    note: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Feedback Schemas
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    """Schema for submitting feedback on a delivered action."""

    action_id: int
    user_id: int
    helpful: bool
    note: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Schema returned after feedback is recorded."""

    id: int
    action_id: int
    user_id: int
    timestamp: datetime
    helpful: bool
    note: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health-check response."""

    status: str = "ok"
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# User Profile Schemas
# ---------------------------------------------------------------------------

class UserProfileResponse(BaseModel):
    """Public representation of a user profile."""

    id: int
    fitbit_user_id: Optional[str] = None
    created_at: datetime
    preferences: Optional[dict] = None

    model_config = {"from_attributes": True}

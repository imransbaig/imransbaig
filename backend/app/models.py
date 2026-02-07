"""SQLAlchemy ORM models for the Agentic Health Coach."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReadingType(str, enum.Enum):
    """Types of sensor readings that can be ingested."""

    heart_rate = "heart_rate"
    steps = "steps"
    sleep = "sleep"
    activity = "activity"


class StateType(str, enum.Enum):
    """Inferred physiological / psychological states."""

    stressed = "stressed"
    calm = "calm"
    fatigued = "fatigued"
    energized = "energized"
    sleep_deprived = "sleep_deprived"


class CueType(str, enum.Enum):
    """User-reported cue categories."""

    stress = "stress"
    pain = "pain"
    mood_low = "mood_low"
    mood_high = "mood_high"
    custom = "custom"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UserProfile(Base):
    """Represents a registered user and their preferences."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fitbit_user_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    sensor_readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    inferred_states: Mapped[list["InferredState"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    actions: Mapped[list["Action"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cue_logs: Mapped[list["CueLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SensorReading(Base):
    """A single sensor data point from a wearable device."""

    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_profiles.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reading_type: Mapped[ReadingType] = mapped_column(
        Enum(ReadingType), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    reading_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Relationships
    user: Mapped["UserProfile"] = relationship(back_populates="sensor_readings")


class InferredState(Base):
    """An inferred physiological or psychological state for a user."""

    __tablename__ = "inferred_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_profiles.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    state_type: Mapped[StateType] = mapped_column(
        Enum(StateType), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    signals: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["UserProfile"] = relationship(back_populates="inferred_states")


class Action(Base):
    """A recommended action for a user, with provenance via reason trace."""

    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_profiles.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_trace: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["UserProfile"] = relationship(back_populates="actions")
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="action", cascade="all, delete-orphan"
    )


class Feedback(Base):
    """User feedback on a delivered action."""

    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("actions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_profiles.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    action: Mapped["Action"] = relationship(back_populates="feedbacks")
    user: Mapped["UserProfile"] = relationship(back_populates="feedbacks")


class CueLog(Base):
    """A user-reported cue (e.g. feeling stressed, in pain)."""

    __tablename__ = "cue_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_profiles.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    cue_type: Mapped[CueType] = mapped_column(Enum(CueType), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["UserProfile"] = relationship(back_populates="cue_logs")

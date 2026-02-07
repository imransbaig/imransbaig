"""SQLAlchemy ORM model for SMS messages managed by the Gatekeeper."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SmsMessage(Base):
    """An incoming SMS message tracked by the SMS Gatekeeper.

    Each message transitions through one of the following statuses:

    * **delivered** -- arrived during business hours and was forwarded
      immediately.
    * **queued** -- arrived outside business hours and is held until the
      next business-hours window.
    * **released** -- was previously queued and has since been released
      (either automatically or manually).
    """

    __tablename__ = "sms_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    twilio_sid: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )

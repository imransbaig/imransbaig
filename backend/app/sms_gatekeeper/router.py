"""FastAPI router for the SMS Gatekeeper.

Provides endpoints for:
* Twilio incoming-message webhook
* Viewing and releasing the message queue
* Inspecting the current business-hours configuration and status
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.sms_gatekeeper.config import BusinessHoursConfig, load_config
from app.sms_gatekeeper.logic import is_business_hours, next_business_open
from app.sms_gatekeeper.models import SmsMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sms", tags=["sms-gatekeeper"])

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

TWIML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'


def _twiml_empty() -> str:
    """Return a TwiML response with no actions (Twilio delivers by default)."""
    return f"{TWIML_HEADER}\n<Response></Response>"


def _twiml_message(text: str) -> str:
    """Return a TwiML response containing a single ``<Message>``."""
    return f"{TWIML_HEADER}\n<Response><Message>{text}</Message></Response>"


def _get_config() -> BusinessHoursConfig:
    """FastAPI dependency that provides the current business-hours config."""
    return load_config()


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/incoming", summary="Twilio webhook for incoming SMS")
def incoming_sms(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(None),
    db: Session = Depends(get_db),
    config: BusinessHoursConfig = Depends(_get_config),
) -> Response:
    """Handle an incoming SMS forwarded by Twilio.

    During business hours the message is stored as *delivered* and an empty
    TwiML response is returned so Twilio completes normal delivery.

    Outside business hours the message is stored as *queued* and Twilio
    receives a friendly auto-reply informing the sender when their message
    will be delivered.
    """
    now = datetime.now(timezone.utc)

    if is_business_hours(now, config):
        msg = SmsMessage(
            from_number=From,
            to_number=To,
            body=Body,
            received_at=now,
            status="delivered",
            delivered_at=now,
            twilio_sid=MessageSid,
        )
        db.add(msg)
        db.commit()
        logger.info("SMS from %s delivered (business hours)", From)
        return Response(content=_twiml_empty(), media_type="text/xml")

    # Outside business hours -- queue the message.
    next_open = next_business_open(now, config)
    next_open_str = next_open.strftime("%A %I:%M %p %Z")

    msg = SmsMessage(
        from_number=From,
        to_number=To,
        body=Body,
        received_at=now,
        status="queued",
        twilio_sid=MessageSid,
    )
    db.add(msg)
    db.commit()
    logger.info("SMS from %s queued (outside business hours)", From)

    reply = (
        "Message received outside business hours. "
        f"It will be delivered when business hours resume at {next_open_str}."
    )
    return Response(content=_twiml_message(reply), media_type="text/xml")


@router.post("/release", summary="Release all queued messages")
def release_queue(
    db: Session = Depends(get_db),
) -> dict:
    """Mark every *queued* message as *released* with the current timestamp.

    Returns the number of messages that were released.
    """
    now = datetime.now(timezone.utc)
    queued = db.query(SmsMessage).filter(SmsMessage.status == "queued").all()
    count = len(queued)
    for msg in queued:
        msg.status = "released"
        msg.delivered_at = now
    db.commit()
    logger.info("Released %d queued message(s)", count)
    return {"released": count}


@router.get("/queue", summary="View queued messages")
def view_queue(
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return a list of all currently queued messages."""
    messages = db.query(SmsMessage).filter(SmsMessage.status == "queued").all()
    return [
        {
            "id": m.id,
            "from_number": m.from_number,
            "body": m.body,
            "received_at": m.received_at.isoformat() if m.received_at else None,
        }
        for m in messages
    ]


@router.get("/config", summary="View business hours configuration")
def view_config(
    config: BusinessHoursConfig = Depends(_get_config),
) -> dict:
    """Return the active business-hours configuration."""
    return config.model_dump()


@router.get("/status", summary="Quick status check")
def status(
    db: Session = Depends(get_db),
    config: BusinessHoursConfig = Depends(_get_config),
) -> dict:
    """Return whether it is currently business hours, the next opening time,
    and the number of queued messages.
    """
    now = datetime.now(timezone.utc)
    in_hours = is_business_hours(now, config)
    next_open = next_business_open(now, config)
    queued_count = (
        db.query(SmsMessage).filter(SmsMessage.status == "queued").count()
    )
    return {
        "is_business_hours": in_hours,
        "next_business_open": next_open.isoformat(),
        "queued_count": queued_count,
    }

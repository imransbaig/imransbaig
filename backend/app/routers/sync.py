"""Router for syncing sensor data from wearable devices (e.g. Fitbit)."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import SensorReading, UserProfile
from app.schemas import SyncRequest, SyncResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post(
    "",
    response_model=SyncResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch-sync sensor readings",
    description=(
        "Accepts a batch of sensor readings from a wearable device, "
        "validates them, and persists them to the database."
    ),
)
def sync_readings(payload: SyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    """Ingest a batch of sensor readings.

    Args:
        payload: A ``SyncRequest`` containing a list of sensor readings.
        db: Database session (injected).

    Returns:
        A ``SyncResponse`` with the number of readings stored.

    Raises:
        HTTPException 404: If the user_id in any reading does not exist.
        HTTPException 422: If the payload is malformed (handled by FastAPI).
    """
    if not payload.readings:
        return SyncResponse(count=0, message="No readings provided")

    # Validate that all referenced users exist (collect unique IDs first)
    user_ids = {r.user_id for r in payload.readings}
    existing_users = (
        db.query(UserProfile.id)
        .filter(UserProfile.id.in_(user_ids))
        .all()
    )
    existing_ids = {u.id for u in existing_users}
    missing = user_ids - existing_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User(s) not found: {sorted(missing)}",
        )

    db_readings: list[SensorReading] = []
    for reading in payload.readings:
        db_reading = SensorReading(
            user_id=reading.user_id,
            timestamp=reading.timestamp or datetime.now(timezone.utc),
            reading_type=reading.reading_type,
            value=reading.value,
            reading_metadata=reading.metadata,
        )
        db_readings.append(db_reading)

    db.add_all(db_readings)
    db.commit()

    count = len(db_readings)
    logger.info("Synced %d sensor readings for user(s) %s", count, sorted(user_ids))
    return SyncResponse(count=count)


@router.get(
    "/fitbit/callback",
    summary="Fitbit OAuth2 callback",
    description=(
        "Handles the Fitbit OAuth2 authorization code callback. "
        "Exchanges the authorization code for an access token and "
        "associates it with the user profile."
    ),
)
def fitbit_oauth_callback(
    code: str = Query(..., description="Authorization code from Fitbit"),
    state: str = Query(default="", description="Opaque state value for CSRF protection"),
) -> dict:
    """Handle the Fitbit OAuth2 redirect.

    In a production deployment this endpoint would:
    1. Verify the ``state`` parameter to prevent CSRF.
    2. Exchange the ``code`` for an access / refresh token pair via the
       Fitbit token endpoint.
    3. Persist the tokens and link them to the user.

    For now it returns a placeholder acknowledging receipt of the code.

    Args:
        code: The authorization code from Fitbit.
        state: The opaque state parameter for CSRF protection.

    Returns:
        A JSON dict confirming the callback was received.
    """
    logger.info(
        "Fitbit OAuth callback received (code=%s..., state=%s)",
        code[:8] if len(code) > 8 else code,
        state,
    )

    # TODO: Exchange authorization code for access + refresh tokens via
    # POST https://api.fitbit.com/oauth2/token using settings.FITBIT_CLIENT_ID
    # and settings.FITBIT_CLIENT_SECRET.  Store tokens securely.

    return {
        "status": "callback_received",
        "message": (
            "Authorization code received. "
            "Token exchange is not yet implemented."
        ),
        "fitbit_client_id_configured": bool(settings.FITBIT_CLIENT_ID),
    }

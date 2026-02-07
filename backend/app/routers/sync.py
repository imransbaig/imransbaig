"""Router for syncing sensor data from wearable devices (e.g. Fitbit)."""

import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import SensorReading, UserProfile
from app.schemas import SyncRequest, SyncResponse
from app.services.fitbit import FitbitAPIError, FitbitService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Module-level Fitbit service instance and in-memory token store
_fitbit = FitbitService()
_tokens: dict[str, dict] = {}  # user_state -> token_response
_csrf_states: dict[str, bool] = {}  # state -> True (valid)


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
    """Ingest a batch of sensor readings."""
    if not payload.readings:
        return SyncResponse(count=0, message="No readings provided")

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


# ---------------------------------------------------------------------------
# Fitbit OAuth2 Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/fitbit/authorize",
    summary="Start Fitbit OAuth2 flow",
    description="Redirects the user to Fitbit's authorization page.",
)
def fitbit_authorize() -> dict:
    """Generate a Fitbit authorization URL.

    Returns the URL the frontend should redirect the user to.
    """
    if not settings.FITBIT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fitbit OAuth not configured. Set FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET in .env",
        )

    csrf_state = secrets.token_urlsafe(32)
    _csrf_states[csrf_state] = True

    url = _fitbit.get_authorize_url(user_state=csrf_state)
    logger.info("Generated Fitbit authorize URL (state=%s...)", csrf_state[:8])
    return {"authorize_url": url, "state": csrf_state}


@router.get(
    "/fitbit/callback",
    summary="Fitbit OAuth2 callback",
    description="Exchanges the authorization code for tokens and stores them.",
)
def fitbit_oauth_callback(
    code: str = Query(..., description="Authorization code from Fitbit"),
    state: str = Query(default="", description="Opaque state value for CSRF protection"),
) -> dict:
    """Handle the Fitbit OAuth2 redirect.

    1. Verify the ``state`` parameter to prevent CSRF.
    2. Exchange the ``code`` for an access / refresh token pair.
    3. Store tokens in memory for data fetching.
    """
    logger.info(
        "Fitbit OAuth callback received (code=%s..., state=%s)",
        code[:8] if len(code) > 8 else code,
        state,
    )

    # CSRF check
    if state and state not in _csrf_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    _csrf_states.pop(state, None)

    if not settings.FITBIT_CLIENT_ID:
        return {
            "status": "error",
            "message": "Fitbit OAuth not configured. Set FITBIT_CLIENT_ID in .env",
        }

    try:
        token_response = _fitbit.exchange_code(code)
    except FitbitAPIError as e:
        logger.error("Fitbit token exchange failed: %s", e)
        return {"status": "error", "message": f"Token exchange failed: {e.detail}"}

    # Store tokens keyed by Fitbit user ID
    fitbit_user_id = token_response.get("user_id", "default")
    _tokens[fitbit_user_id] = token_response

    logger.info("Fitbit tokens stored for user %s", fitbit_user_id)
    return {
        "status": "connected",
        "fitbit_user_id": fitbit_user_id,
        "message": "Fitbit account connected successfully!",
    }


@router.get(
    "/fitbit/status",
    summary="Check Fitbit connection status",
)
def fitbit_status() -> dict:
    """Check if a Fitbit account is connected and tokens are available."""
    configured = bool(settings.FITBIT_CLIENT_ID)
    connected = len(_tokens) > 0
    users = list(_tokens.keys()) if connected else []
    return {
        "configured": configured,
        "connected": connected,
        "connected_users": users,
    }


@router.post(
    "/fitbit/pull",
    summary="Pull latest data from Fitbit",
    description="Fetch heart rate, sleep, and step data from the Fitbit API.",
)
def fitbit_pull(
    date: str = Query(default="today", description="Date in YYYY-MM-DD format or 'today'"),
    fitbit_user_id: str = Query(default="", description="Fitbit user ID (uses first connected if empty)"),
) -> dict:
    """Pull data from the Fitbit API and run it through the coach engine.

    Returns the fetched reading counts and the coach cycle result.
    """
    # Find tokens
    if fitbit_user_id and fitbit_user_id in _tokens:
        token_data = _tokens[fitbit_user_id]
    elif _tokens:
        fitbit_user_id = next(iter(_tokens))
        token_data = _tokens[fitbit_user_id]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Fitbit account connected. Use /api/sync/fitbit/authorize first.",
        )

    access_token = token_data.get("access_token", "")

    try:
        readings = _fitbit.fetch_all(access_token, date)
    except FitbitAPIError as e:
        # Try refreshing the token
        refresh = token_data.get("refresh_token")
        if refresh:
            try:
                new_tokens = _fitbit.refresh_token(refresh)
                _tokens[fitbit_user_id] = new_tokens
                access_token = new_tokens["access_token"]
                readings = _fitbit.fetch_all(access_token, date)
            except FitbitAPIError:
                raise HTTPException(status_code=401, detail="Fitbit token expired. Please re-authorize.")
        else:
            raise HTTPException(status_code=401, detail=f"Fitbit API error: {e.detail}")

    # Run through coach engine
    from app.routers.coach import _engine
    result = _engine.process(
        user_id=f"fitbit_{fitbit_user_id}",
        readings=readings,
        mode="passive",
    )

    hr_count = sum(1 for r in readings if r.reading_type == "heart_rate")
    sleep_count = sum(1 for r in readings if r.reading_type == "sleep")
    step_count = sum(1 for r in readings if r.reading_type == "steps")

    return {
        "status": "synced",
        "date": date,
        "readings": {
            "heart_rate": hr_count,
            "sleep": sleep_count,
            "steps": step_count,
            "total": len(readings),
        },
        "coach_result": result.to_dict(),
    }

"""Router for logging user-reported cues."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CueLog, UserProfile
from app.schemas import CueCreate, CueResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cue", tags=["cue"])


@router.post(
    "",
    response_model=CueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a user cue",
    description=(
        "Records a user-reported cue such as stress, pain, or mood change. "
        "Cues are used alongside sensor data to improve state inference."
    ),
)
def log_cue(
    payload: CueCreate,
    db: Session = Depends(get_db),
) -> CueResponse:
    """Persist a user-reported cue.

    Args:
        payload: The cue data to log.
        db: Database session (injected).

    Returns:
        The created ``CueResponse``.

    Raises:
        HTTPException 404: If the user does not exist.
    """
    # Verify the user exists
    user = db.query(UserProfile).filter(UserProfile.id == payload.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {payload.user_id} not found",
        )

    cue = CueLog(
        user_id=payload.user_id,
        timestamp=datetime.now(timezone.utc),
        cue_type=payload.cue_type,
        note=payload.note,
    )
    db.add(cue)
    db.commit()
    db.refresh(cue)

    logger.info(
        "Logged cue %s for user %d (id=%d)",
        cue.cue_type.value,
        payload.user_id,
        cue.id,
    )
    return cue

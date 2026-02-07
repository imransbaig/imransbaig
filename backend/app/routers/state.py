"""Router for retrieving inferred user states."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InferredState, UserProfile
from app.schemas import InferredStateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get(
    "/{user_id}",
    response_model=InferredStateResponse,
    summary="Get latest inferred state",
    description=(
        "Returns the most recent inferred physiological / psychological "
        "state for the given user."
    ),
)
def get_latest_state(
    user_id: int,
    db: Session = Depends(get_db),
) -> InferredStateResponse:
    """Retrieve the latest inferred state for a user.

    Args:
        user_id: The user's primary key.
        db: Database session (injected).

    Returns:
        The most recent ``InferredStateResponse`` for the user.

    Raises:
        HTTPException 404: If the user does not exist or has no inferred states.
    """
    # Verify the user exists
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    latest_state = (
        db.query(InferredState)
        .filter(InferredState.user_id == user_id)
        .order_by(InferredState.timestamp.desc())
        .first()
    )

    if latest_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inferred state found for user {user_id}",
        )

    logger.info(
        "Returning inferred state %s (confidence=%.2f) for user %d",
        latest_state.state_type.value,
        latest_state.confidence,
        user_id,
    )
    return latest_state

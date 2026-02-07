"""Router for logging user feedback on delivered actions."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Action, Feedback, UserProfile
from app.schemas import FeedbackCreate, FeedbackResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log feedback on an action",
    description=(
        "Records whether a delivered action was helpful, along with an "
        "optional free-text note. Feedback is used to improve future "
        "action recommendations."
    ),
)
def log_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """Persist feedback on a delivered action.

    Args:
        payload: The feedback data.
        db: Database session (injected).

    Returns:
        The created ``FeedbackResponse``.

    Raises:
        HTTPException 404: If the user or action does not exist.
        HTTPException 400: If the action has not been delivered yet.
    """
    # Verify user exists
    user = db.query(UserProfile).filter(UserProfile.id == payload.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {payload.user_id} not found",
        )

    # Verify action exists
    action = db.query(Action).filter(Action.id == payload.action_id).first()
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {payload.action_id} not found",
        )

    # Only allow feedback on delivered actions
    if not action.delivered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Action {payload.action_id} has not been delivered yet. "
                "Feedback can only be submitted for delivered actions."
            ),
        )

    feedback = Feedback(
        action_id=payload.action_id,
        user_id=payload.user_id,
        timestamp=datetime.now(timezone.utc),
        helpful=payload.helpful,
        note=payload.note,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    logger.info(
        "Feedback %d logged for action %d by user %d (helpful=%s)",
        feedback.id,
        payload.action_id,
        payload.user_id,
        payload.helpful,
    )
    return feedback

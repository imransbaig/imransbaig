"""Router for retrieving and managing recommended actions."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Action, UserProfile
from app.schemas import ActionDeliverResponse, ActionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/action", tags=["action"])


@router.get(
    "/{user_id}",
    response_model=ActionResponse,
    summary="Get next best action",
    description=(
        "Returns the next best undelivered action for the given user, "
        "including the full reason trace explaining why it was recommended."
    ),
)
def get_next_action(
    user_id: int,
    db: Session = Depends(get_db),
) -> ActionResponse:
    """Retrieve the next best action for a user.

    Selects the most recent action that has not yet been delivered or
    dismissed.

    Args:
        user_id: The user's primary key.
        db: Database session (injected).

    Returns:
        The next ``ActionResponse`` with its reason trace.

    Raises:
        HTTPException 404: If the user does not exist or has no pending actions.
    """
    # Verify the user exists
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    next_action = (
        db.query(Action)
        .filter(
            Action.user_id == user_id,
            Action.delivered.is_(False),
            Action.dismissed.is_(False),
        )
        .order_by(Action.timestamp.desc())
        .first()
    )

    if next_action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pending actions for user {user_id}",
        )

    logger.info(
        "Returning action %d (%s) for user %d",
        next_action.id,
        next_action.action_type,
        user_id,
    )
    return next_action


@router.post(
    "/{action_id}/deliver",
    response_model=ActionDeliverResponse,
    summary="Mark action as delivered",
    description="Marks a specific action as having been delivered to the user.",
)
def deliver_action(
    action_id: int,
    db: Session = Depends(get_db),
) -> ActionDeliverResponse:
    """Mark an action as delivered.

    Args:
        action_id: The action's primary key.
        db: Database session (injected).

    Returns:
        An ``ActionDeliverResponse`` confirming delivery.

    Raises:
        HTTPException 404: If the action does not exist.
        HTTPException 409: If the action was already delivered.
    """
    action = db.query(Action).filter(Action.id == action_id).first()
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found",
        )

    if action.delivered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Action {action_id} is already marked as delivered",
        )

    action.delivered = True
    db.commit()
    db.refresh(action)

    logger.info("Action %d marked as delivered", action_id)
    return ActionDeliverResponse(id=action.id, delivered=True)

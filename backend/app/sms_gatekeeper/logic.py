"""Core time-based logic for the SMS Gatekeeper.

All functions are pure (no side-effects) and accept an explicit
``BusinessHoursConfig`` so they remain easy to test and never rely on
hard-coded values.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.sms_gatekeeper.config import BusinessHoursConfig


def is_business_hours(dt: datetime, config: BusinessHoursConfig) -> bool:
    """Return ``True`` if *dt* falls within the configured business hours.

    The incoming *dt* may be naive (assumed UTC), UTC-aware, or in any other
    timezone -- it will be converted to the config timezone before the check.

    When the gatekeeper is disabled (``config.enabled is False``) this always
    returns ``True`` so that messages pass through unconditionally.

    Parameters:
        dt: The datetime to evaluate.
        config: Business hours configuration.

    Returns:
        Whether the datetime falls within business hours.
    """
    if not config.enabled:
        return True

    local_dt = _to_local(dt, config)
    weekday = local_dt.weekday()  # 0=Monday
    hour = local_dt.hour

    if weekday not in config.business_days:
        return False

    return config.start_hour <= hour < config.end_hour


def next_business_open(dt: datetime, config: BusinessHoursConfig) -> datetime:
    """Return the next datetime when business hours start.

    If *dt* is already within business hours the *next* opening is still
    returned (i.e. the following business day's start), which is useful for
    informational messages such as "your message will be delivered at ...".

    The returned datetime is in the config timezone.

    Parameters:
        dt: The reference datetime.
        config: Business hours configuration.

    Returns:
        A timezone-aware datetime representing the next business-hours opening.
    """
    local_dt = _to_local(dt, config)

    # Start searching from the next candidate point.
    # If we are before start_hour on a business day, today could be the answer.
    candidate = local_dt.replace(
        hour=config.start_hour, minute=0, second=0, microsecond=0
    )

    # If the candidate is still in the future on a business day, use it.
    if candidate > local_dt and candidate.weekday() in config.business_days:
        return candidate

    # Otherwise advance day-by-day until we land on a business day.
    candidate += timedelta(days=1)
    candidate = candidate.replace(
        hour=config.start_hour, minute=0, second=0, microsecond=0
    )
    for _ in range(7):
        if candidate.weekday() in config.business_days:
            return candidate
        candidate += timedelta(days=1)

    # Fallback -- should never happen if business_days is non-empty.
    return candidate


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _to_local(dt: datetime, config: BusinessHoursConfig) -> datetime:
    """Convert *dt* to the config timezone.

    Naive datetimes are assumed to be UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(config.tz)

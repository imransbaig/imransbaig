"""Business hours configuration for the SMS Gatekeeper.

Loads settings from the SMS_BUSINESS_HOURS environment variable (JSON string)
with sensible defaults for a standard Mon-Fri 9-5 Eastern schedule.
"""

import json
import os
from zoneinfo import ZoneInfo

from pydantic import BaseModel


class BusinessHoursConfig(BaseModel):
    """Defines when incoming SMS messages should be forwarded immediately
    versus held in a queue.

    Attributes:
        timezone: IANA timezone name used for all business-hours checks.
        start_hour: Hour (0-23) when business hours begin each business day.
        end_hour: Hour (0-23) when business hours end each business day.
        business_days: Weekday indices where 0=Monday .. 6=Sunday.
        enabled: Master switch; when False the gatekeeper forwards everything.
    """

    timezone: str = "America/New_York"
    start_hour: int = 9
    end_hour: int = 17
    business_days: list[int] = [0, 1, 2, 3, 4]
    enabled: bool = True

    @property
    def tz(self) -> ZoneInfo:
        """Return a ``ZoneInfo`` object for the configured timezone."""
        return ZoneInfo(self.timezone)


def load_config() -> BusinessHoursConfig:
    """Load business hours configuration.

    Reads the ``SMS_BUSINESS_HOURS`` environment variable.  If the variable is
    set it must contain a valid JSON object whose keys correspond to
    :class:`BusinessHoursConfig` fields.  Missing keys fall back to their
    defaults.  If the variable is unset the pure-default config is returned.
    """
    raw = os.environ.get("SMS_BUSINESS_HOURS")
    if raw:
        data = json.loads(raw)
        return BusinessHoursConfig(**data)
    return BusinessHoursConfig()

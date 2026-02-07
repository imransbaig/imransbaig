"""Fitbit Web API integration service.

Handles the full OAuth2 authorization flow and fetches heart-rate, sleep,
and step data, returning normalised ``SensorData`` objects that the rest of
the application can consume directly.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import List
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.signals.feature_extractor import SensorData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FITBIT_AUTHORIZE_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_API_BASE = "https://api.fitbit.com"

OAUTH_SCOPES = "heartrate sleep activity profile"

# Sleep-stage name -> integer mapping aligned with feature_extractor
# (0=awake, 1=light, 2=deep, 3=REM).
_SLEEP_STAGE_MAP: dict[str, int] = {
    "wake": 0,
    "awake": 0,
    "restless": 0,
    "light": 1,
    "deep": 2,
    "rem": 3,
}


class FitbitAPIError(Exception):
    """Raised when a Fitbit API call returns a non-success status."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Fitbit API error {status_code}: {detail}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _basic_auth_header() -> str:
    """Return the Base64-encoded ``client_id:client_secret`` for Basic auth."""
    raw = f"{settings.FITBIT_CLIENT_ID}:{settings.FITBIT_CLIENT_SECRET}"
    encoded = base64.b64encode(raw.encode()).decode()
    return f"Basic {encoded}"


def _bearer_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _parse_date(date_str: str) -> datetime:
    """Parse a ``YYYY-MM-DD`` date string into a ``datetime`` at midnight."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def _combine_date_time(date_str: str, time_str: str) -> datetime:
    """Combine ``YYYY-MM-DD`` and ``HH:MM:SS`` into a single ``datetime``."""
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class FitbitService:
    """Synchronous client for the Fitbit Web API.

    All network calls use ``httpx.Client`` so they block the calling thread.
    For async contexts, wrap calls in ``asyncio.to_thread``.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    # -- OAuth2 -------------------------------------------------------------

    def get_authorize_url(self, user_state: str) -> str:
        """Build the Fitbit OAuth2 authorization URL.

        Parameters
        ----------
        user_state:
            An opaque string the caller uses to prevent CSRF.  It is passed
            through as the OAuth2 ``state`` parameter.

        Returns
        -------
        str
            The full authorization URL the user should be redirected to.
        """
        params = {
            "response_type": "code",
            "client_id": settings.FITBIT_CLIENT_ID,
            "redirect_uri": settings.FITBIT_REDIRECT_URI,
            "scope": OAUTH_SCOPES,
            "state": user_state,
        }
        return f"{FITBIT_AUTHORIZE_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        """Exchange an authorization code for an access / refresh token pair.

        Parameters
        ----------
        code:
            The authorization code received on the redirect callback.

        Returns
        -------
        dict
            The full token response from Fitbit (access_token, refresh_token,
            expires_in, token_type, user_id, scope).

        Raises
        ------
        FitbitAPIError
            If the token endpoint returns a non-2xx status.
        """
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                FITBIT_TOKEN_URL,
                headers={
                    "Authorization": _basic_auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.FITBIT_REDIRECT_URI,
                },
            )

        if response.status_code != 200:
            raise FitbitAPIError(response.status_code, response.text)

        return response.json()

    def refresh_token(self, refresh_token: str) -> dict:
        """Use a refresh token to obtain a new access token.

        Parameters
        ----------
        refresh_token:
            A valid Fitbit refresh token.

        Returns
        -------
        dict
            The refreshed token response (same shape as ``exchange_code``).

        Raises
        ------
        FitbitAPIError
            If the token endpoint returns a non-2xx status.
        """
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                FITBIT_TOKEN_URL,
                headers={
                    "Authorization": _basic_auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )

        if response.status_code != 200:
            raise FitbitAPIError(response.status_code, response.text)

        return response.json()

    # -- Data fetching ------------------------------------------------------

    def _get(self, access_token: str, path: str) -> dict:
        """Perform an authenticated GET against the Fitbit API.

        Parameters
        ----------
        access_token:
            A valid Fitbit access token.
        path:
            The API path (appended to ``FITBIT_API_BASE``).

        Returns
        -------
        dict
            The parsed JSON response body.

        Raises
        ------
        FitbitAPIError
            If the response status code is not 2xx.
        """
        url = f"{FITBIT_API_BASE}{path}"
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(url, headers=_bearer_header(access_token))

        if not response.is_success:
            raise FitbitAPIError(response.status_code, response.text)

        return response.json()

    # -- Heart rate ---------------------------------------------------------

    def fetch_heart_rate(
        self,
        access_token: str,
        date: str = "today",
    ) -> List[SensorData]:
        """Fetch intraday heart-rate data for the given date.

        Parameters
        ----------
        access_token:
            A valid Fitbit access token.
        date:
            Date string in ``YYYY-MM-DD`` format or ``"today"``.

        Returns
        -------
        list[SensorData]
            One ``SensorData`` per minute of recorded heart-rate data.
        """
        path = f"/1/user/-/activities/heart/date/{date}/1d/1min.json"
        data = self._get(access_token, path)

        # Resolve the actual date string (needed when date="today").
        actual_date = (
            data.get("activities-heart", [{}])[0].get("dateTime", date)
        )
        if actual_date == "today":
            actual_date = datetime.utcnow().strftime("%Y-%m-%d")

        dataset = (
            data.get("activities-heart-intraday", {})
            .get("dataset", [])
        )

        results: list[SensorData] = []
        for entry in dataset:
            time_str = entry.get("time", "00:00:00")
            bpm = entry.get("value", 0)
            ts = _combine_date_time(actual_date, time_str)
            results.append(
                SensorData(
                    reading_type="heart_rate",
                    value=float(bpm),
                    timestamp=ts,
                    metadata={"time": time_str, "source": "fitbit"},
                ),
            )

        logger.debug("Fetched %d heart-rate readings for %s", len(results), actual_date)
        return results

    # -- Sleep --------------------------------------------------------------

    def fetch_sleep(
        self,
        access_token: str,
        date: str = "today",
    ) -> List[SensorData]:
        """Fetch sleep-stage data for the given date.

        Parameters
        ----------
        access_token:
            A valid Fitbit access token.
        date:
            Date string in ``YYYY-MM-DD`` format or ``"today"``.

        Returns
        -------
        list[SensorData]
            One ``SensorData`` per sleep-stage segment.  ``value`` encodes the
            stage as an integer (0=awake, 1=light, 2=deep, 3=REM) consistent
            with ``feature_extractor.extract_sleep_features``.
        """
        path = f"/1.2/user/-/sleep/date/{date}.json"
        data = self._get(access_token, path)

        results: list[SensorData] = []
        for sleep_log in data.get("sleep", []):
            levels = sleep_log.get("levels", {})
            level_data = levels.get("data", [])

            for segment in level_data:
                stage_name = segment.get("level", "wake").lower()
                stage_int = _SLEEP_STAGE_MAP.get(stage_name, 0)
                duration_seconds = segment.get("seconds", 0)
                duration_minutes = duration_seconds / 60.0

                # Fitbit sleep timestamps are full ISO-8601 strings.
                dt_str = segment.get("dateTime", "")
                try:
                    ts = datetime.fromisoformat(dt_str)
                except (ValueError, TypeError):
                    logger.warning("Skipping sleep segment with bad timestamp: %s", dt_str)
                    continue

                results.append(
                    SensorData(
                        reading_type="sleep",
                        value=float(stage_int),
                        timestamp=ts,
                        metadata={
                            "stage": stage_name,
                            "duration_minutes": round(duration_minutes, 2),
                            "source": "fitbit",
                        },
                    ),
                )

        logger.debug("Fetched %d sleep segments for %s", len(results), date)
        return results

    # -- Steps --------------------------------------------------------------

    def fetch_steps(
        self,
        access_token: str,
        date: str = "today",
    ) -> List[SensorData]:
        """Fetch intraday step data (15-min intervals) for the given date.

        Parameters
        ----------
        access_token:
            A valid Fitbit access token.
        date:
            Date string in ``YYYY-MM-DD`` format or ``"today"``.

        Returns
        -------
        list[SensorData]
            One ``SensorData`` per 15-minute bucket with ``value`` equal to
            the step count for that interval.
        """
        path = f"/1/user/-/activities/steps/date/{date}/1d/15min.json"
        data = self._get(access_token, path)

        actual_date = (
            data.get("activities-steps", [{}])[0].get("dateTime", date)
        )
        if actual_date == "today":
            actual_date = datetime.utcnow().strftime("%Y-%m-%d")

        dataset = (
            data.get("activities-steps-intraday", {})
            .get("dataset", [])
        )

        results: list[SensorData] = []
        for entry in dataset:
            time_str = entry.get("time", "00:00:00")
            steps = entry.get("value", 0)
            ts = _combine_date_time(actual_date, time_str)
            results.append(
                SensorData(
                    reading_type="steps",
                    value=float(steps),
                    timestamp=ts,
                    metadata={"time": time_str, "source": "fitbit"},
                ),
            )

        logger.debug("Fetched %d step readings for %s", len(results), actual_date)
        return results

    # -- Combined -----------------------------------------------------------

    def fetch_all(
        self,
        access_token: str,
        date: str = "today",
    ) -> List[SensorData]:
        """Fetch heart-rate, sleep, and step data and combine the results.

        Parameters
        ----------
        access_token:
            A valid Fitbit access token.
        date:
            Date string in ``YYYY-MM-DD`` format or ``"today"``.

        Returns
        -------
        list[SensorData]
            Combined list sorted by timestamp.
        """
        hr = self.fetch_heart_rate(access_token, date)
        sleep = self.fetch_sleep(access_token, date)
        steps = self.fetch_steps(access_token, date)

        combined = hr + sleep + steps
        combined.sort(key=lambda s: s.timestamp)
        return combined

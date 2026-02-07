"""Tests for the Fitbit service and sync router endpoints."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.fitbit import FitbitService, FitbitAPIError, _combine_date_time
from app.signals.feature_extractor import SensorData


# ---------------------------------------------------------------------------
# Test DB setup
# ---------------------------------------------------------------------------

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=_engine)


def _override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _setup_tables():
    app.dependency_overrides[get_db] = _override_db
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


client = TestClient(app)


# ---------------------------------------------------------------------------
# FitbitService unit tests
# ---------------------------------------------------------------------------

class TestFitbitServiceUnit:
    def test_get_authorize_url(self):
        svc = FitbitService()
        url = svc.get_authorize_url("test_state_123")
        assert "https://www.fitbit.com/oauth2/authorize" in url
        assert "test_state_123" in url
        assert "heartrate" in url
        assert "sleep" in url
        assert "activity" in url

    def test_combine_date_time(self):
        result = _combine_date_time("2025-01-15", "14:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30

    def test_fitbit_api_error(self):
        err = FitbitAPIError(401, "Token expired")
        assert err.status_code == 401
        assert "Token expired" in err.detail
        assert "401" in str(err)


# ---------------------------------------------------------------------------
# Fitbit sync router tests
# ---------------------------------------------------------------------------

class TestFitbitSyncRouter:
    def test_fitbit_status_unconfigured(self):
        r = client.get("/api/sync/fitbit/status")
        assert r.status_code == 200
        data = r.json()
        assert "configured" in data
        assert "connected" in data
        assert data["connected"] is False

    def test_fitbit_authorize_without_config(self):
        r = client.get("/api/sync/fitbit/authorize")
        # Should return 503 when FITBIT_CLIENT_ID is empty
        assert r.status_code == 503

    def test_fitbit_callback_without_config(self):
        r = client.get("/api/sync/fitbit/callback?code=test_code")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "error"

    def test_fitbit_pull_without_connection(self):
        r = client.post("/api/sync/fitbit/pull")
        assert r.status_code == 400
        assert "No Fitbit account connected" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Coach API with Fitbit-like data
# ---------------------------------------------------------------------------

class TestCoachWithFitbitData:
    def test_coach_process_returns_valid_structure(self):
        r = client.post(
            "/api/coach/process",
            json={"user_id": "fitbit_test", "mode": "passive"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "inferred_state" in data
        assert "state" in data["inferred_state"]
        assert "confidence" in data["inferred_state"]

    def test_coach_feedback(self):
        # First get an action
        r = client.post(
            "/api/coach/process",
            json={"user_id": "fb_test", "mode": "live"},
        )
        data = r.json()
        action_id = data.get("action_id")
        if action_id:
            r2 = client.post(
                "/api/coach/feedback",
                json={"action_id": action_id, "helpful": True},
            )
            assert r2.status_code == 200

    def test_coach_reset(self):
        r = client.post("/api/coach/reset?user_id=fitbit_test")
        assert r.status_code == 200
        assert r.json()["reset"] is True

    def test_coach_builds_trend_after_multiple_cycles(self):
        for _ in range(4):
            r = client.post(
                "/api/coach/process",
                json={"user_id": "trend_test", "mode": "passive"},
            )
        data = r.json()
        assert data["trend_summary"] is not None
        assert "dominant_state" in data["trend_summary"]
        assert "state_distribution" in data["trend_summary"]

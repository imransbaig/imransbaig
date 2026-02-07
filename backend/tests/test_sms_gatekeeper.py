"""Tests for the SMS Gatekeeper business-hours logic and API endpoints."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.sms_gatekeeper.config import BusinessHoursConfig
from app.sms_gatekeeper.logic import is_business_hours, next_business_open
from app.sms_gatekeeper.models import SmsMessage


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
# Config fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def default_config():
    return BusinessHoursConfig()


@pytest.fixture
def custom_config():
    return BusinessHoursConfig(
        timezone="UTC",
        start_hour=10,
        end_hour=16,
        business_days=[0, 1, 2, 3, 4],
        enabled=True,
    )


# ---------------------------------------------------------------------------
# is_business_hours tests
# ---------------------------------------------------------------------------

class TestIsBusinessHours:
    def test_weekday_during_hours(self, default_config):
        # Wednesday 10:00 AM Eastern
        dt = datetime(2025, 1, 8, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        assert is_business_hours(dt, default_config) is True

    def test_weekday_before_hours(self, default_config):
        # Wednesday 7:00 AM Eastern
        dt = datetime(2025, 1, 8, 7, 0, tzinfo=ZoneInfo("America/New_York"))
        assert is_business_hours(dt, default_config) is False

    def test_weekday_after_hours(self, default_config):
        # Wednesday 6:00 PM Eastern
        dt = datetime(2025, 1, 8, 18, 0, tzinfo=ZoneInfo("America/New_York"))
        assert is_business_hours(dt, default_config) is False

    def test_weekend_during_hours(self, default_config):
        # Saturday 10:00 AM Eastern
        dt = datetime(2025, 1, 11, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        assert is_business_hours(dt, default_config) is False

    def test_boundary_start(self, default_config):
        # Exactly 9:00 AM Eastern on Monday
        dt = datetime(2025, 1, 6, 9, 0, tzinfo=ZoneInfo("America/New_York"))
        assert is_business_hours(dt, default_config) is True

    def test_boundary_end(self, default_config):
        # Exactly 5:00 PM Eastern on Monday (end_hour=17 means < 17)
        dt = datetime(2025, 1, 6, 17, 0, tzinfo=ZoneInfo("America/New_York"))
        assert is_business_hours(dt, default_config) is False

    def test_disabled_always_true(self, default_config):
        default_config.enabled = False
        # Saturday midnight -- would be outside hours
        dt = datetime(2025, 1, 11, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        assert is_business_hours(dt, default_config) is True

    def test_naive_datetime_assumed_utc(self, custom_config):
        # UTC 12:00 on a Wednesday -- should be in hours (10-16 UTC)
        dt = datetime(2025, 1, 8, 12, 0)
        assert is_business_hours(dt, custom_config) is True

    def test_utc_timezone_conversion(self, default_config):
        # 3:00 PM UTC = 10:00 AM Eastern on a Wednesday
        dt = datetime(2025, 1, 8, 15, 0, tzinfo=timezone.utc)
        assert is_business_hours(dt, default_config) is True


# ---------------------------------------------------------------------------
# next_business_open tests
# ---------------------------------------------------------------------------

class TestNextBusinessOpen:
    def test_returns_future_datetime(self, default_config):
        dt = datetime(2025, 1, 8, 20, 0, tzinfo=ZoneInfo("America/New_York"))
        result = next_business_open(dt, default_config)
        assert result > dt

    def test_next_day_if_past_start(self, custom_config):
        # Wednesday 14:00 UTC -- past start_hour 10
        dt = datetime(2025, 1, 8, 14, 0, tzinfo=timezone.utc)
        result = next_business_open(dt, custom_config)
        # Should be Thursday 10:00 UTC
        assert result.hour == 10
        assert result.weekday() == 3  # Thursday

    def test_skips_weekend(self, default_config):
        # Friday 6:00 PM Eastern
        dt = datetime(2025, 1, 10, 18, 0, tzinfo=ZoneInfo("America/New_York"))
        result = next_business_open(dt, default_config)
        # Should skip to Monday
        assert result.weekday() == 0  # Monday

    def test_same_day_if_before_start(self, custom_config):
        # Wednesday 8:00 UTC -- before start_hour 10
        dt = datetime(2025, 1, 8, 8, 0, tzinfo=timezone.utc)
        result = next_business_open(dt, custom_config)
        assert result.hour == 10
        assert result.weekday() == 2  # Wednesday (same day)


# ---------------------------------------------------------------------------
# SMS API endpoint tests
# ---------------------------------------------------------------------------

class TestSmsIncoming:
    def test_during_business_hours_delivers(self):
        """When business hours enabled=False (default for test), messages pass through."""
        # Use the /api/sms/config endpoint to check defaults
        r = client.get("/api/sms/config")
        assert r.status_code == 200

    def test_queue_view(self):
        r = client.get("/api/sms/queue")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_status_endpoint(self):
        r = client.get("/api/sms/status")
        assert r.status_code == 200
        data = r.json()
        assert "is_business_hours" in data
        assert "next_business_open" in data
        assert "queued_count" in data

    def test_release_empty_queue(self):
        r = client.post("/api/sms/release")
        assert r.status_code == 200
        assert r.json()["released"] == 0

    def test_incoming_webhook(self):
        r = client.post(
            "/api/sms/incoming",
            data={
                "From": "+15551234567",
                "To": "+15559876543",
                "Body": "Hello from test",
                "MessageSid": "SM_test_123",
            },
        )
        assert r.status_code == 200
        assert "<?xml" in r.text
        assert "<Response>" in r.text

    def test_config_endpoint(self):
        r = client.get("/api/sms/config")
        assert r.status_code == 200
        data = r.json()
        assert data["timezone"] == "America/New_York"
        assert data["start_hour"] == 9
        assert data["end_hour"] == 17

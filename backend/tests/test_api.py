"""Integration tests for the FastAPI endpoints."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import UserProfile, Action


# Use an in-memory SQLite database for tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop after."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    # Seed a test user
    db = TestSessionLocal()
    user = db.query(UserProfile).filter(UserProfile.id == 1).first()
    if not user:
        user = UserProfile(id=1, fitbit_user_id="test-fitbit-id", preferences={})
        db.add(user)
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestSyncEndpoint:
    def test_sync_sensor_readings(self, client):
        payload = {
            "readings": [
                {
                    "user_id": 1,
                    "reading_type": "heart_rate",
                    "value": 75.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"source": "fitbit"},
                },
                {
                    "user_id": 1,
                    "reading_type": "steps",
                    "value": 1200.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"period": "hourly"},
                },
            ],
        }
        response = client.post("/api/sync", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 2

    def test_sync_empty_readings(self, client):
        payload = {"readings": []}
        response = client.post("/api/sync", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 0


class TestStateEndpoint:
    def test_get_state_no_data(self, client):
        """Should return 404 when user has no inferred states."""
        response = client.get("/api/state/1")
        assert response.status_code == 404

    def test_get_state_user_not_found(self, client):
        """Should return 404 for non-existent user."""
        response = client.get("/api/state/999")
        assert response.status_code == 404


class TestActionEndpoint:
    def test_get_next_action_none_pending(self, client):
        """Should return 404 when no pending actions."""
        response = client.get("/api/action/1")
        assert response.status_code == 404

    def test_deliver_action_not_found(self, client):
        """Should return 404 for non-existent action."""
        response = client.post("/api/action/999/deliver")
        assert response.status_code == 404


class TestCueEndpoint:
    def test_log_cue(self, client):
        payload = {
            "user_id": 1,
            "cue_type": "stress",
            "note": "Stressful meeting",
        }
        response = client.post("/api/cue", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["cue_type"] == "stress"

    def test_log_cue_user_not_found(self, client):
        payload = {
            "user_id": 999,
            "cue_type": "stress",
            "note": "Test",
        }
        response = client.post("/api/cue", json=payload)
        assert response.status_code == 404


class TestFeedbackEndpoint:
    def test_submit_feedback_action_not_found(self, client):
        payload = {
            "action_id": 999,
            "user_id": 1,
            "helpful": True,
            "note": "This really helped",
        }
        response = client.post("/api/feedback", json=payload)
        assert response.status_code == 404

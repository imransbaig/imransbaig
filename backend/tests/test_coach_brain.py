"""Tests for the Coach Brain (trigger registry + action selector)."""

import pytest
from datetime import datetime, timedelta
from app.signals.state_inferrer import InferredStateResult
from app.brain.trigger_registry import TriggerRegistry, TriggeredAction
from app.brain.action_selector import ActionSelector, ActionDelivery, SelectedAction
from app.brain.reason_tracer import ReasonTracer


@pytest.fixture
def registry():
    return TriggerRegistry()


@pytest.fixture
def selector():
    return ActionSelector()


@pytest.fixture
def tracer():
    return ReasonTracer()


class TestTriggerRegistry:
    def test_elevated_hr_sedentary_trigger(self, registry):
        """Should trigger breathing exercise when HR elevated and sedentary."""
        state = InferredStateResult(state="stressed", confidence=0.8, contributing_signals={})
        features = {
            "hr_features": {"mean_hr": 95, "resting_hr_estimate": 68, "hr_variability_rmssd": 20},
            "activity_features": {"sedentary_minutes": 300, "active_minutes": 30},
            "context_features": {"time_of_day": "afternoon", "hour": 14},
        }
        history = []
        triggered = registry.evaluate(state, features, history)
        action_types = [t.action_type for t in triggered]
        assert "breathing_exercise_2min" in action_types

    def test_prolonged_sedentary_trigger(self, registry):
        """Should trigger movement break when sedentary > 45 min."""
        state = InferredStateResult(state="calm", confidence=0.7, contributing_signals={})
        features = {
            "hr_features": {"mean_hr": 72, "resting_hr_estimate": 68, "hr_variability_rmssd": 50},
            "activity_features": {"sedentary_minutes": 60, "active_minutes": 10},
            "context_features": {"time_of_day": "afternoon", "hour": 14},
        }
        history = []
        triggered = registry.evaluate(state, features, history)
        action_types = [t.action_type for t in triggered]
        assert "movement_break" in action_types

    def test_poor_sleep_morning_trigger(self, registry):
        """Should trigger gentle morning routine for sleep-deprived in morning."""
        state = InferredStateResult(state="sleep_deprived", confidence=0.85, contributing_signals={})
        features = {
            "hr_features": {"mean_hr": 80, "resting_hr_estimate": 75, "hr_variability_rmssd": 30},
            "activity_features": {"sedentary_minutes": 30, "active_minutes": 5},
            "sleep_features": {"sleep_duration_hours": 4, "sleep_efficiency": 0.5},
            "context_features": {"time_of_day": "morning", "hour": 8},
        }
        history = []
        triggered = registry.evaluate(state, features, history)
        action_types = [t.action_type for t in triggered]
        assert "gentle_morning_routine" in action_types

    def test_evening_wind_down_trigger(self, registry):
        """Should trigger wind-down when stressed after 9 PM."""
        state = InferredStateResult(state="stressed", confidence=0.75, contributing_signals={})
        features = {
            "hr_features": {"mean_hr": 88, "resting_hr_estimate": 68, "hr_variability_rmssd": 25},
            "activity_features": {"sedentary_minutes": 120, "active_minutes": 30},
            "context_features": {"time_of_day": "night", "hour": 22},
        }
        history = []
        triggered = registry.evaluate(state, features, history)
        action_types = [t.action_type for t in triggered]
        assert "wind_down_routine" in action_types

    def test_triggers_sorted_by_priority(self, registry):
        """Triggered actions should be sorted by priority (highest first)."""
        state = InferredStateResult(state="stressed", confidence=0.9, contributing_signals={})
        features = {
            "hr_features": {"mean_hr": 98, "resting_hr_estimate": 68, "hr_variability_rmssd": 18},
            "activity_features": {"sedentary_minutes": 300, "active_minutes": 10},
            "context_features": {"time_of_day": "afternoon", "hour": 14},
        }
        history = []
        triggered = registry.evaluate(state, features, history)
        if len(triggered) > 1:
            priorities = [t.priority for t in triggered]
            assert priorities == sorted(priorities, reverse=True)

    def test_positive_reinforcement_trigger(self, registry):
        """Should trigger encouragement when calm after being stressed."""
        state = InferredStateResult(state="calm", confidence=0.8, contributing_signals={})
        features = {
            "hr_features": {"mean_hr": 70, "resting_hr_estimate": 65, "hr_variability_rmssd": 50},
            "activity_features": {"sedentary_minutes": 60, "active_minutes": 60},
            "context_features": {"time_of_day": "afternoon", "hour": 15},
        }
        history = [
            InferredStateResult(state="stressed", confidence=0.7, contributing_signals={}),
            InferredStateResult(state="stressed", confidence=0.8, contributing_signals={}),
            InferredStateResult(state="calm", confidence=0.6, contributing_signals={}),
        ]
        triggered = registry.evaluate(state, features, history)
        action_types = [t.action_type for t in triggered]
        assert "encouragement_nudge" in action_types


class TestActionSelector:
    def test_selects_highest_priority(self, selector):
        """Should select the first (highest priority) action from sorted list."""
        actions = [
            TriggeredAction(
                trigger_name="elevated_hr_sedentary",
                action_type="breathing_exercise_2min",
                priority=8,
                cooldown_minutes=30,
                explanation_template="Take a breath.",
            ),
            TriggeredAction(
                trigger_name="prolonged_sedentary",
                action_type="movement_break",
                priority=6,
                cooldown_minutes=60,
                explanation_template="Time to move.",
            ),
        ]
        result = selector.select(actions, user_history=[], mode="passive")
        assert result is not None
        assert result.action_type == "breathing_exercise_2min"

    def test_cooldown_respected(self, selector):
        """Should skip action within cooldown window."""
        actions = [
            TriggeredAction(
                trigger_name="elevated_hr_sedentary",
                action_type="breathing_exercise_2min",
                priority=8,
                cooldown_minutes=30,
                explanation_template="Take a breath.",
            ),
        ]
        recent_history = [
            ActionDelivery(
                action_type="breathing_exercise_2min",
                trigger_name="elevated_hr_sedentary",
                delivered_at=datetime.utcnow() - timedelta(minutes=10),
                dismissed=False,
            )
        ]
        result = selector.select(actions, user_history=recent_history, mode="passive")
        assert result is None

    def test_live_mode_reduced_cooldown(self, selector):
        """In live mode, cooldowns should be reduced by 50%."""
        actions = [
            TriggeredAction(
                trigger_name="elevated_hr_sedentary",
                action_type="breathing_exercise_2min",
                priority=8,
                cooldown_minutes=30,
                explanation_template="Take a breath.",
            ),
        ]
        # Delivered 20 min ago: within 30 min passive cooldown, but outside 15 min live cooldown
        recent_history = [
            ActionDelivery(
                action_type="breathing_exercise_2min",
                trigger_name="elevated_hr_sedentary",
                delivered_at=datetime.utcnow() - timedelta(minutes=20),
                dismissed=False,
            )
        ]
        result = selector.select(actions, user_history=recent_history, mode="live")
        assert result is not None

    def test_fatigue_check(self, selector):
        """Should skip action if user dismissed last 2 of same type."""
        actions = [
            TriggeredAction(
                trigger_name="elevated_hr_sedentary",
                action_type="breathing_exercise_2min",
                priority=8,
                cooldown_minutes=30,
                explanation_template="Take a breath.",
            ),
        ]
        dismissed_history = [
            ActionDelivery(
                action_type="breathing_exercise_2min",
                trigger_name="elevated_hr_sedentary",
                delivered_at=datetime.utcnow() - timedelta(hours=2),
                dismissed=True,
            ),
            ActionDelivery(
                action_type="breathing_exercise_2min",
                trigger_name="elevated_hr_sedentary",
                delivered_at=datetime.utcnow() - timedelta(hours=1),
                dismissed=True,
            ),
        ]
        result = selector.select(actions, user_history=dismissed_history, mode="passive")
        assert result is None

    def test_returns_none_when_no_actions(self, selector):
        """Should return None when no actions triggered."""
        result = selector.select([], user_history=[], mode="passive")
        assert result is None


class TestReasonTracer:
    def test_generate_trace(self, tracer):
        """Should generate a valid reason trace."""
        trace = tracer.generate(
            trigger_name="elevated_hr_sedentary",
            signals={"heart_rate_bpm": 92, "activity_level": "sedentary"},
            inference="stress_likely",
            action_type="breathing_exercise_2min",
            explanation_template="Your heart rate was {heart_rate_bpm} bpm while {activity_level}; a 2-minute reset usually helps.",
            confidence=0.78,
        )
        assert "trace_id" in trace
        assert "timestamp" in trace
        assert trace["trigger"] == "elevated_hr_sedentary"
        assert trace["action"] == "breathing_exercise_2min"
        assert "92" in trace["explanation"]
        assert trace["confidence"] == 0.78

    def test_trace_has_all_fields(self, tracer):
        """Trace should contain all required schema fields."""
        trace = tracer.generate(
            trigger_name="test_trigger",
            signals={"key": "value"},
            inference="test_inference",
            action_type="test_action",
            explanation_template="Test explanation.",
            confidence=0.5,
        )
        required_fields = ["trace_id", "timestamp", "trigger", "signals",
                          "inference", "action", "explanation", "confidence"]
        for field in required_fields:
            assert field in trace, f"Missing field: {field}"

    def test_safe_template_rendering(self, tracer):
        """Missing template keys should be replaced with '?'."""
        trace = tracer.generate(
            trigger_name="test",
            signals={"known_key": "value"},
            inference="test",
            action_type="test",
            explanation_template="Key is {known_key} and missing is {missing_key}.",
            confidence=0.5,
        )
        assert "value" in trace["explanation"]
        assert "?" in trace["explanation"]

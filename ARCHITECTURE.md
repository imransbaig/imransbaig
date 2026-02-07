# Agentic Health Coach — Architecture Overview

## System Goal
Real-time iOS health coach that monitors physiological signals (Fitbit),
contextual cues (user input, time-of-day), and behavioral patterns to
deliver personalized stress-reduction interventions via an agentic loop.

## Agentic Loop
```
SENSE → INFER STATE → PLAN NEXT ACTION → ACT → LEARN
```

| Phase        | Passive Mode          | Live Mode               |
|--------------|-----------------------|--------------------------|
| Sense        | Poll every 15 min     | Stream every 60 sec      |
| Infer        | Batch scoring         | Real-time scoring        |
| Plan         | Queue nudge           | Immediate intervention   |
| Act          | Local notification    | In-app overlay + haptic  |
| Learn        | Nightly feedback loop | Session-end feedback     |

## Module Boundaries

### 1. iOS App (SwiftUI)
- **TodayView**: Next Best Action card, Downshift Now, Log Cue, Start Live Mode
- **LiveModeView**: Active session with real-time feedback
- **TrustPanel**: Reason-trace explanations for every recommendation
- **CueLogger**: Widget + Siri shortcut for user cue input
- **FitbitSync**: OAuth2 PKCE flow → REST polling
- **Accessibility**: Dynamic Type, VoiceOver labels, Reduce Motion support

### 2. Backend (FastAPI + Postgres)
- **/api/sync**: Receive Fitbit data batches
- **/api/state**: Return current inferred user state
- **/api/action**: Return next best action
- **/api/cue**: Log user-reported cue
- **/api/feedback**: Log action outcome (learn phase)
- **Models**: UserProfile, SensorReading, InferredState, Action, Feedback

### 3. Data/Signals Agent
- Feature extraction from raw sensor data
- Stress proxy scoring (elevated HR + sedentary + time-of-day)
- Sleep quality scoring (duration + efficiency + restlessness)
- Trend detection (rolling 7-day windows)

### 4. Coach Brain (Trigger Registry)
- Rule engine with weighted triggers
- Action selection with cooldown + fatigue logic
- Personalization layer (user feedback history)
- Reason-trace generation for every decision

## Reason-Trace Schema
```json
{
  "trace_id": "uuid",
  "timestamp": "ISO-8601",
  "trigger": "elevated_hr_sedentary",
  "signals": {
    "heart_rate_bpm": 92,
    "activity_level": "sedentary",
    "time_context": "afternoon_work"
  },
  "inference": "stress_likely",
  "action": "breathing_exercise_2min",
  "explanation": "Your heart rate was elevated while sedentary; a 2-minute reset usually helps.",
  "confidence": 0.78
}
```

## Tech Stack
- **iOS**: Swift 5.9+, SwiftUI, HealthKit (future), WidgetKit
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic, Postgres 15
- **Infra**: Docker Compose (API + DB)
- **Auth**: Fitbit OAuth2 PKCE

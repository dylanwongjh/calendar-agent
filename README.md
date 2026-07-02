---
title: Calendar Agent
emoji: 📅
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Calendar Agent

A Flask-based backend server that leverages LLMs (Gemini via OpenRouter) to parse natural-language text and timetable images into structured calendar events and alarms. This backend is designed to integrate seamlessly with tools like iOS Shortcuts for automated scheduling.

## Features

- **Natural Language Parsing**: Translates raw text queries (e.g., `"Basketball Practice 830-1030pm 7th July"`) into structured event creation, deletion, or alarm-setting instructions.
- **Visual Timetable Extraction**: Uses vision-based models to extract weekly class slots and exam schedules from uploaded timetable screenshots.
- **Smart Alarm Integration**: Automatically queues wake-up alarms for events scheduled within the next 24 hours.
- **Context-Aware Handling**: Computes relative dates, infers missing time details, and asks clarification questions when instructions are ambiguous.

---

## API Reference

### 1. Parse Event
Parses a natural language instruction into a calendar event, deletion action, or alarm.

* **URL**: `/parse-event`
* **Method**: `POST`
* **Headers**: `Content-Type: application/json`
* **Request Body**:
  ```json
  {
    "text": "Basketball Practice 830-1030pm 7th July"
  }
  ```
* **Response**:
  ```json
  {
    "action": "create_event",
    "args": {
      "title": "Basketball Practice",
      "start": "2026-07-07T20:30:00+08:00",
      "end": "2026-07-07T22:30:00+08:00",
      "needs_clarification": false
    },
    "actions": [
      {
        "action": "create_event",
        "args": { ... }
      }
    ]
  }
  ```

### 2. Parse Timetable
Extracts structured weekly timetables and exams from a base64/URL screenshot of a calendar/schedule.

* **URL**: `/parse-timetable`
* **Method**: `POST`
* **Headers**: `Content-Type: application/json`
* **Request Body**:
  ```json
  {
    "image": "data:image/png;base64,..."
  }
  ```

### 3. Alarm Queue Management

* **Get Pending Alarms**: `GET /api/alarms/pending`
* **Clear Queue**: `POST /api/alarms/clear`

---

## Setup & Local Development

### Prerequisites
- Python 3.11+
- An OpenRouter API Key

### Configuration
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Run Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the application:
   ```bash
   python app.py
   ```
3. Open http://localhost:7860 to access the playground UI.

> [!NOTE]
> The app runs on port `7860` by default to match Hugging Face Spaces requirements.

---

## Deployment

This repository is configured for deployment to **Hugging Face Spaces** using the Docker SDK.

* The configuration is defined in the [Dockerfile](file:///Users/dylanwong/Downloads/NUHS_Intern/calendar-agent/calendar-agent/Dockerfile).
* Production WSGI execution is pre-configured for Render/production via Gunicorn in [render.yaml](file:///Users/dylanwong/Downloads/NUHS_Intern/calendar-agent/calendar-agent/render.yaml).
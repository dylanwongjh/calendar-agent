---
title: Calendar Agent
emoji: 📅
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Calendar Agent Backend

Parses natural-language event text into structured JSON for the "Add Event" iOS Shortcut.

## Endpoint
POST /parse-event
Body: {"text": "Basketball Practice 830-1030pm 7th July"}
Returns: {"title": ..., "start": ..., "end": ..., "location": ..., "needs_clarification": ...}

## Setup
- Set ANTHROPIC_API_KEY as an environment variable (or HF Spaces secret in production).
- Local run: `python app.py`, then POST to http://localhost:7860/parse-event

## Deployment
Hosted on Hugging Face Spaces (Docker SDK), same pattern as ERIICA.
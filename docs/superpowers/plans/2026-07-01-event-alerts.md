# Event Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add custom alarm/alert capabilities to the Calendar Agent for important/urgent events with minimal token overhead.

**Architecture:** Extend backend OpenAI tool schema to accept `alert_minutes`, update system prompts to query the user if urgent/important events are parsed without reminders, and inject `VALARM` blocks into frontend-generated `.ics` files.

**Tech Stack:** Python (Flask), JavaScript (Vanilla HTML5)

---

### Task 1: Update tool schema and system prompt in `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add `alert_minutes` to `CREATE_EVENT_TOOL`**
  Modify the parameter schema:
  ```python
  CREATE_EVENT_TOOL = {
      "type": "function",
      "function": {
          "name": "create_event",
          "description": "Create a calendar event from parsed natural language",
          "parameters": {
              "type": "object",
              "properties": {
                  "title": {"type": "string"},
                  "start": {"type": "string", "description": "ISO 8601 datetime with timezone offset"},
                  "end": {"type": "string", "description": "ISO 8601 datetime with timezone offset"},
                  "location": {"type": "string"},
                  "notes": {"type": "string"},
                  "alert_minutes": {"type": "integer", "description": "Minutes before start time to set an alert/reminder (optional)"},
                  "needs_clarification": {"type": "boolean"},
                  "clarification_question": {"type": "string"}
              },
              "required": ["title"]
          }
      }
  }
  ```

- [ ] **Step 2: Update `build_system_prompt`**
  Modify system prompt to handle reminders and urgent/important event clarifications:
  ```python
  def build_system_prompt(now):
      return f"""You are a calendar parsing assistant. Current date/time: {now.isoformat()} (Singapore time, SGT/UTC+8).
  
  Extract event details from the user's message and call either create_event or delete_event. You MUST call one of these functions — do not reply in plain text.
  
  For event creation:
  - Call create_event.
  - Always assume Asia/Singapore timezone unless stated otherwise; output start/end as ISO 8601 with +08:00 offset.
  - For all-day or multi-day events with no specific times (e.g., "Leadership Camp from 5th to 7th July"), set all_day=true, and set start/end to 'YYYY-MM-DD' representing the start and end dates (inclusive as described by the user).
  - For multi-day events with specific times (e.g., "Training course from July 10 9am to July 12 5pm"), set start and end to the respective dates and times as ISO 8601.
  - If no year is given, assume the current year, or next year if that date has already passed this year.
  - Interpret bare times like "830" using context: an evening activity or PM cue means 8:30 PM; if genuinely ambiguous, set needs_clarification=true and ask rather than guessing.
  - If only a start time is given with no duration, default to a 1-hour event.
  - For relative dates ("next Tuesday", "this Friday"), compute precisely from the current date given above — never guess.
  - Keep titles concise; move extra detail into the notes field.
  - Parse any explicit reminders/alerts requested by the user (e.g. "remind me 15m before", "alert 1 hour before") into alert_minutes (integer value in minutes).
  - If the user uses keywords indicating importance or urgency (e.g. "important", "urgent", "critical", "must attend") but DOES NOT specify any reminder time, set needs_clarification=true and ask: "This event seems important. Would you like to set a reminder? If so, when (e.g., 15 minutes before, 1 hour before)?"
  
  For event deletion/removal:
  - Call delete_event.
  - Use this if the user wants to cancel, remove, or delete an event (e.g. "cancel Basketball Practice", "remove the exam prep session").
  - Try to extract the title and the date of the event they want to remove.
  """
  ```

---

### Task 2: Update frontend ICS generator and event saving logic

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Update single event creation flow to store `alert_minutes`**
  Modify single event creation `newEvent` assignment to include `alert_minutes`:
  ```javascript
            const newEvent = {
              uid: uid,
              title: args.title,
              start: args.start,
              end: args.end,
              location: args.location || '',
              notes: args.notes || '',
              all_day: args.all_day || false,
              alert_minutes: args.alert_minutes !== undefined ? args.alert_minutes : null
            };
  ```

- [ ] **Step 2: Update `generateICS` helper to write `VALARM` component**
  Inside `generateICS`, update both the all-day and standard event blocks to include a `VALARM` block if `alert_minutes` is set:
  ```javascript
      const alarmLines = (event.alert_minutes !== null && event.alert_minutes !== undefined) ? [
        'BEGIN:VALARM',
        `TRIGGER:-PT${event.alert_minutes}M`,
        'ACTION:DISPLAY',
        'DESCRIPTION:Reminder',
        'END:VALARM'
      ] : [];
  ```
  And join/inject these lines before the final `END:VEVENT`.
  
  Updated standard VEVENT template:
  ```javascript
        return [
          'BEGIN:VCALENDAR',
          'VERSION:2.0',
          'PRODID:-//Calendar Agent//EN',
          'BEGIN:VEVENT',
          `UID:${uid}`,
          `DTSTAMP:${created}`,
          `DTSTART:${start}`,
          `DTEND:${end}`,
          `SUMMARY:${event.title}`,
          `DESCRIPTION:${event.notes || ''}`,
          `LOCATION:${event.location || ''}`,
          ...alarmLines,
          'END:VEVENT',
          'END:VCALENDAR'
        ].join('\r\n');
  ```

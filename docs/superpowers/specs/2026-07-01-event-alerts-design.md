# Event Alerts Design Spec

This document details how the Calendar Agent will support custom event alerts/reminders, utilizing the existing natural language parser and clarification flow.

## Proposed Changes

### Backend (`app.py`)

1. **Tool Schema Update**:
   * Add optional integer property `alert_minutes` to `CREATE_EVENT_TOOL` representing the number of minutes before the event start time to set an alert.

2. **System Prompt Updates**:
   * Update the system prompt to instruct the AI to:
     * Extract alert/reminder offsets (e.g., "15 minutes before", "1 hour prior") and set `alert_minutes` accordingly.
     * Detect keywords indicating importance or urgency (e.g. "important", "urgent", "critical", "must attend"). If such a keyword is detected but no alert is specified, set `needs_clarification = true` and prompt the user to confirm if they want an alert and when.

### Frontend (`templates/index.html`)

1. **Saved Event Schema**:
   * Include `alert_minutes` (number or null) in the event object saved to `localStorage` and inside `newEvent`.

2. **ICS Generation**:
   * If `alert_minutes` is set on the event, inject a `VALARM` block into the `generateICS` output:
     ```
     BEGIN:VEVENT
     ...
     BEGIN:VALARM
     TRIGGER:-PT{alert_minutes}M
     ACTION:DISPLAY
     DESCRIPTION:Reminder
     END:VALARM
     END:VEVENT
     ```

## Verification Plan

### Manual Verification
1. Parse: "Important: Meeting with boss at 3pm tomorrow".
2. Confirm the agent responds asking if you want to set a reminder and when.
3. Parse: "Important: Meeting with boss at 3pm tomorrow. Remind me 15 minutes before".
4. Confirm event is created successfully, the ICS downloads, and contains:
   ```
   BEGIN:VALARM
   TRIGGER:-PT15M
   ACTION:DISPLAY
   DESCRIPTION:Reminder
   END:VALARM
   ```

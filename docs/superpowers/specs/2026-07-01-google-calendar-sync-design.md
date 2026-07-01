# Google Calendar Manual Sync Design

This document describes the design for adding Google Calendar sync capability via pre-filled template links, keeping token usage and backend complexity to a minimum.

## Proposed Changes

### UI Components (`templates/index.html`)

1. **Google Calendar URL Generator**:
   * Implement a JavaScript function `generateGoogleCalendarUrl(event)` that constructs a template link:
     `https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={dates}&details={notes}&location={location}`
   * Correctly convert local SGT dates/times (`event.start` and `event.end`) into UTC strings in `YYYYMMDDTHHMMSSZ` format for timed events, and `YYYYMMDD` format for all-day events to ensure timezone consistency.

2. **Single Event Action**:
   * Update the submit button handler: after creating the `.ics` file, show a success status message that contains a link/button: "Add to Google Calendar".
   * This button will open the generated Google Calendar URL in a new window/tab.

3. **Scheduled Events Table**:
   * Add a new column or update the action column in the "My Scheduled Events" table to include an "Add to Google" button next to each event.

4. **Timetable Import Instructions**:
   * Add a small help tip banner or text label under the "Generate & Download ICS Calendar" button guiding Android/Google Calendar users to import the generated `.ics` file via the Google Calendar web interface (`Settings > Import & export`).

## Verification Plan

### Manual Verification
1. Parse a single event (e.g. "Basketball practice 8:30pm to 10:30pm on 7th July").
2. Verify the "Add to Google Calendar" button appears in the status message.
3. Click the button and check if it opens a Google Calendar page with correct title, SGT timezone converted to UTC, notes, and location.
4. Verify the "Add to Google" button is present in the "My Scheduled Events" table and functions correctly.

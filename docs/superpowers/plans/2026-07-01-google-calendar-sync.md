# Google Calendar Manual Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to easily add their parsed calendar events and academic timetable to Google Calendar via pre-filled URLs and user guide tips.

**Architecture:** Entirely client-side URL generation for single events, plus helpful UI guides instructing users how to import the downloaded ICS file for full timetable schedules.

**Tech Stack:** JavaScript (Vanilla HTML5)

---

### Task 1: Implement Google Calendar URL Generator function in JS

**Files:**
- Modify: `templates/index.html` (around the existing helper functions in the script block)

- [ ] **Step 1: Write helper function `generateGoogleCalendarUrl`**
  Add the following JavaScript function after `generateICS` in `templates/index.html`:
  ```javascript
  function generateGoogleCalendarUrl(event) {
    const isDateOnly = (str) => /^\d{4}-\d{2}-\d{2}$/.test(str);
    const isAllDay = event.all_day || (isDateOnly(event.start) && isDateOnly(event.end));
    
    let datesParam = '';
    if (isAllDay) {
      // Format YYYYMMDD for all-day events
      const parseDate = (str) => {
        const m = str.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
        return new Date(str);
      };
      const startDate = parseDate(event.start);
      const endDate = parseDate(event.end);
      endDate.setDate(endDate.getDate() + 1); // DTEND is exclusive

      const start = formatDateToICSAllDay(startDate);
      const end = formatDateToICSAllDay(endDate);
      datesParam = `${start}/${end}`;
    } else {
      // Format YYYYMMDDTHHMMSSZ in UTC
      const formatToUTCString = (dateObj) => {
        return dateObj.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
      };
      const start = formatToUTCString(new Date(event.start));
      const end = formatToUTCString(new Date(event.end));
      datesParam = `${start}/${end}`;
    }

    const baseUrl = 'https://calendar.google.com/calendar/render?action=TEMPLATE';
    const params = [
      `text=${encodeURIComponent(event.title)}`,
      `dates=${datesParam}`,
      `details=${encodeURIComponent(event.notes || '')}`,
      `location=${encodeURIComponent(event.location || '')}`
    ];
    return `${baseUrl}&${params.join('&')}`;
  }
  ```

- [ ] **Step 2: Verify the helper formats dates correctly**
  Verify the logic by checking if it correctly handles timezone offsets and encodes SGT times as UTC (e.g. SGT 20:30 converts to UTC 12:30).

---

### Task 2: Update Single Event Submit Flow with "Add to Google Calendar" button

**Files:**
- Modify: `templates/index.html` (under single event parsing flow)

- [ ] **Step 1: Update submit click handler to show Google Calendar link**
  Modify the `action === 'create_event'` success handler block to render the link in the status message.
  
  Target content:
  ```javascript
          if (action === 'create_event') {
            statusMsg.className = 'status success';
            statusMsg.textContent = 'Creating .ics file...';
  
            const uid = `${Date.now()}@calendaragent`;
            const newEvent = {
              uid: uid,
              title: args.title,
              start: args.start,
              end: args.end,
              location: args.location || '',
              notes: args.notes || '',
              all_day: args.all_day || false
            };
  
            const icsContent = generateICS(newEvent);
            const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `${args.title.replace(/\s+/g, '_') || 'event'}.ics`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
  
            // Save event
            const currentEvents = getStoredEvents();
            currentEvents.push(newEvent);
            saveStoredEvents(currentEvents);
  
            statusMsg.textContent = `Successfully created event "${args.title}"! Tap the downloaded file to add to calendar.`;
            eventInput.value = '';
  ```
  
  Replacement content:
  ```javascript
          if (action === 'create_event') {
            statusMsg.className = 'status success';
            statusMsg.textContent = 'Creating .ics file...';
  
            const uid = `${Date.now()}@calendaragent`;
            const newEvent = {
              uid: uid,
              title: args.title,
              start: args.start,
              end: args.end,
              location: args.location || '',
              notes: args.notes || '',
              all_day: args.all_day || false
            };
  
            const icsContent = generateICS(newEvent);
            const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `${args.title.replace(/\s+/g, '_') || 'event'}.ics`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
  
            // Save event
            const currentEvents = getStoredEvents();
            currentEvents.push(newEvent);
            saveStoredEvents(currentEvents);
  
            const gCalUrl = generateGoogleCalendarUrl(newEvent);
            statusMsg.innerHTML = `Successfully created event "${args.title}"! <br>` +
              `1. <span style="color: var(--text-muted);">Local Apple Calendar:</span> Tap the downloaded .ics file.<br>` +
              `2. <span style="color: var(--text-muted);">Google Calendar:</span> <a href="${gCalUrl}" target="_blank" style="color: var(--accent); text-decoration: underline; font-weight: 600;">Add to Google Calendar</a>`;
            eventInput.value = '';
  ```

---

### Task 3: Update Scheduled Events Table with "Add to Google" action

**Files:**
- Modify: `templates/index.html` (the `renderSavedEvents` function and table layout)

- [ ] **Step 1: Update renderSavedEvents table template**
  Modify `renderSavedEvents` to append an "Add to Google" button or link inside the Action column.
  
  Target content:
  ```javascript
      events.forEach(evt => {
        const tr = document.createElement('tr');
        const dateObj = new Date(evt.start);
        const formattedDate = isNaN(dateObj.getTime()) ? evt.start : dateObj.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
        tr.innerHTML = `
          <td><strong>${evt.title}</strong><br><span style="font-size: 11px; color: var(--text-muted);">${evt.notes || ''}</span></td>
          <td>${formattedDate}</td>
          <td>${evt.location || 'N/A'}</td>
          <td><button class="delete-btn" onclick="deleteEventById('${evt.uid}')">Delete</button></td>
        `;
        tbody.appendChild(tr);
      });
  ```
  
  Replacement content:
  ```javascript
      events.forEach(evt => {
        const tr = document.createElement('tr');
        const dateObj = new Date(evt.start);
        const formattedDate = isNaN(dateObj.getTime()) ? evt.start : dateObj.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
        const gCalUrl = generateGoogleCalendarUrl(evt);
        tr.innerHTML = `
          <td><strong>${evt.title}</strong><br><span style="font-size: 11px; color: var(--text-muted);">${evt.notes || ''}</span></td>
          <td>${formattedDate}</td>
          <td>${evt.location || 'N/A'}</td>
          <td>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <a href="${gCalUrl}" target="_blank" class="tab-btn" style="text-align: center; background: var(--accent-success); color: #fff; padding: 6px 12px; font-size: 11px; border-radius: 8px; text-decoration: none; display: inline-block;">Add to Google</a>
              <button class="delete-btn" onclick="deleteEventById('${evt.uid}')">Delete</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
  ```

---

### Task 4: Add Google Calendar import guide/tip for Timetable

**Files:**
- Modify: `templates/index.html` (under the timetable's preview container)

- [ ] **Step 1: Append import instructions below "Generate & Download ICS Calendar" button**
  Add a container containing instructions for importing the generated ICS file to Google Calendar.
  
  Target content:
  ```html
          <button id="generateCalendarBtn" class="generate-btn">Generate & Download ICS Calendar</button>
        </div>
      </div>
    </div>
  ```
  
  Replacement content:
  ```html
          <button id="generateCalendarBtn" class="generate-btn">Generate & Download ICS Calendar</button>
          
          <div style="margin-top: 16px; background: rgba(56, 189, 248, 0.08); border: 1px dashed var(--accent); padding: 16px; border-radius: 12px; font-size: 13px;">
            <strong style="color: var(--accent); display: block; margin-bottom: 6px;">Android / Google Calendar User Guide:</strong>
            1. Click "Generate & Download ICS Calendar" to download the file.<br>
            2. Open <a href="https://calendar.google.com" target="_blank" style="color: var(--accent); text-decoration: underline;">Google Calendar Web</a> on your computer.<br>
            3. Go to <strong>Settings (gear icon) &gt; Import &amp; export</strong>.<br>
            4. Select the downloaded `.ics` file, choose your calendar, and click <strong>Import</strong>.
          </div>
        </div>
      </div>
    </div>
  ```

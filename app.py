from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import json
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "google/gemini-2.5-flash"
SGT = pytz.timezone("Asia/Singapore")

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

DELETE_EVENT_TOOL = {
    "type": "function",
    "function": {
        "name": "delete_event",
        "description": "Delete or cancel a calendar event from parsed natural language",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The title of the event to delete"},
                "date": {"type": "string", "description": "Optional date of the event (e.g. YYYY-MM-DD)"},
                "needs_clarification": {"type": "boolean"},
                "clarification_question": {"type": "string"}
            },
            "required": ["title"]
        }
    }
}

CREATE_ALARM_TOOL = {
    "type": "function",
    "function": {
        "name": "create_alarm",
        "description": "Set a wake-up alarm for a specific time and label. Only call this tool if the alarm is for today or tomorrow (within the next 24 hours). Do NOT call this tool for alarms further in the future.",
        "parameters": {
            "type": "object",
            "properties": {
                "time": {"type": "string", "description": "Format: HH:MM, 24-hour format (e.g. 07:00, 19:30)"},
                "label": {"type": "string", "description": "Label/name for the alarm (e.g. Basketball Practice Prep)"}
            },
            "required": ["time", "label"]
        }
    }
}


ALARMS_FILE = os.path.join(os.path.dirname(__file__), "alarms.json")

def get_pending_alarms():
    if not os.path.exists(ALARMS_FILE):
        return []
    try:
        with open(ALARMS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_pending_alarms(alarms):
    try:
        with open(ALARMS_FILE, "w") as f:
            json.dump(alarms, f)
    except Exception:
        pass


PARSE_TIMETABLE_TOOL = {
    "type": "function",
    "function": {
        "name": "parsed_timetable",
        "description": "Extract structured timetable slots and exam schedules from the image",
        "parameters": {
            "type": "object",
            "properties": {
                "slots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "course_code": {"type": "string", "description": "e.g., BN2102, ES2631"},
                            "course_name": {"type": "string", "description": "Full name of the course, e.g., Bioengineering Data Analysis"},
                            "class_type": {"type": "string", "description": "e.g., LEC [1], TUT [2], LAB [1], SEC [G11]"},
                            "day_of_week": {"type": "string", "enum": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]},
                            "start_time": {"type": "string", "description": "HH:MM format, e.g., 09:00, 14:30"},
                            "end_time": {"type": "string", "description": "HH:MM format, e.g., 11:00, 17:00"},
                            "location": {"type": "string", "description": "e.g., LT2, ENG-AUD, E-Learning"},
                            "weeks": {
                                "type": "string", 
                                "description": "Weeks details exactly as written, e.g., 'All weeks', 'Weeks 2-13', 'Weeks 4, 6, 8, 10, 12'"
                            }
                        },
                        "required": ["course_code", "class_type", "day_of_week", "start_time", "end_time", "location", "weeks"]
                    }
                },
                "exams": {
                    "type": "array",
                    "description": "List of exams extracted from the timetable legend/labels",
                    "items": {
                        "type": "object",
                        "properties": {
                            "course_code": {"type": "string", "description": "e.g., BN2204"},
                            "course_name": {"type": "string", "description": "e.g., Fundamentals of Biomechanics"},
                            "date": {"type": "string", "description": "Format: DD-MMM-YYYY, e.g., 25-Apr-2026. Use null or empty string if 'No Exam'"},
                            "time": {"type": "string", "description": "Format: h:mm A or HH:MM, e.g., 9:00 AM, 1:00 PM. Use null or empty string if 'No Exam'"},
                            "duration_hours": {"type": "number", "description": "Duration in hours, e.g., 2. Use null or empty if 'No Exam'"},
                            "has_exam": {"type": "boolean", "description": "true if the course has an exam, false if No Exam"}
                        },
                        "required": ["course_code", "course_name", "has_exam"]
                    }
                }
            },
            "required": ["slots", "exams"]
        }
    }
}

def build_system_prompt(now):
    return f"""You are a calendar and alarm parsing assistant. Current date/time: {now.isoformat()} (Singapore time, SGT/UTC+8).

Extract event or alarm details from the user's message and call the appropriate functions: create_event, delete_event, or create_alarm. You MUST call one or more of these functions — do not reply in plain text.

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
- Parse any explicit alerts/reminders requested by the user (e.g. "remind me 15m before", "alert 1 hour before") into alert_minutes (integer value in minutes).
- If the user uses keywords indicating importance or urgency (e.g. "important", "urgent", "critical", "must attend") but DOES NOT specify any reminder time, set needs_clarification=true and ask: "This event seems important. Would you like to set a reminder? If so, when (e.g., 15 minutes before, 1 hour before)?"

For event deletion/removal:
- Call delete_event.
- Use this if the user wants to cancel, remove, or delete an event (e.g. "cancel Basketball Practice", "remove the exam prep session").
- Try to extract the title and the date of the event they want to remove.

For alarm setting:
- Call create_alarm ONLY if the alarm is for today, tomorrow, or within the next 24 hours (e.g., "wake up tomorrow at 7am", "set alarm for 7:00 AM").
- If the user requests an alarm for a date further in the future (more than 24 hours away, e.g. "set alarm for July 7th" when today is July 1st), do NOT call create_alarm. Only call create_event, and append a note about the alarm to the event description.
- Set the time in HH:MM format (24-hour clock, e.g., "07:00" or "19:30").
- Provide a helpful label (e.g., "Wake up for Basketball Practice").
- If the user wants to set an alarm as part of an event happening tomorrow, call BOTH create_event (for the event) and create_alarm (for the wake-up alarm).

"""

@app.route("/parse-event", methods=["POST"])
def parse_event():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    now = datetime.now(SGT)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt(now)},
            {"role": "user", "content": text}
        ],
        tools=[CREATE_EVENT_TOOL, DELETE_EVENT_TOOL, CREATE_ALARM_TOOL],
        tool_choice="auto",
        max_tokens=500,
    )

    message = response.choices[0].message
    if message.tool_calls:
        actions = []
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name == "create_alarm":
                # Append to persistent alarms queue
                alarms = get_pending_alarms()
                alarms.append({
                    "time": args.get("time"),
                    "label": args.get("label"),
                    "created_at": datetime.now(SGT).isoformat()
                })
                save_pending_alarms(alarms)
                
            actions.append({
                "action": func_name,
                "args": args
            })
            
        # Return first action for backward compatibility, and the complete actions array
        return jsonify({
            "action": actions[0]["action"],
            "args": actions[0]["args"],
            "actions": actions
        })

    return jsonify({"error": "Could not parse event or alarm", "raw": message.content}), 400

@app.route("/api/alarms/pending", methods=["GET"])
def api_pending_alarms():
    return jsonify(get_pending_alarms())

@app.route("/api/alarms/clear", methods=["POST"])
def api_clear_alarms():
    save_pending_alarms([])
    return jsonify({"status": "success", "message": "Pending alarms cleared"})


@app.route("/parse-timetable", methods=["POST"])
def parse_timetable():
    data = request.get_json(silent=True) or {}
    image_data_url = data.get("image", "").strip()
    if not image_data_url:
        return jsonify({"error": "No image data provided"}), 400

    try:
        # Request with OpenRouter
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all weekly course timetable slots from the grid, and map them to their corresponding full names and exam schedules from the legend/labels in the screenshot."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url
                            }
                        }
                    ]
                }
            ],
            tools=[PARSE_TIMETABLE_TOOL],
            tool_choice={"type": "function", "function": {"name": "parsed_timetable"}},
            max_tokens=2000,
        )

        message = response.choices[0].message
        if message.tool_calls:
            args = json.loads(message.tool_calls[0].function.arguments)
            return jsonify(args)

        return jsonify({"error": "Failed to parse timetable from image", "raw": message.content}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
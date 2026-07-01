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
                "needs_clarification": {"type": "boolean"},
                "clarification_question": {"type": "string"}
            },
            "required": ["title"]
        }
    }
}

PARSE_TIMETABLE_TOOL = {
    "type": "function",
    "function": {
        "name": "parsed_timetable",
        "description": "Extract structured timetable slots from the image",
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
                }
            },
            "required": ["slots"]
        }
    }
}

def build_system_prompt(now):
    return f"""You are a calendar parsing assistant. Current date/time: {now.isoformat()} (Singapore time, SGT/UTC+8).

Extract event details from the user's message and call create_event. You MUST call the function — do not reply in plain text.

Rules:
- Always assume Asia/Singapore timezone unless stated otherwise; output start/end as ISO 8601 with +08:00 offset.
- If no year is given, assume the current year, or next year if that date has already passed this year.
- Interpret bare times like "830" using context: an evening activity or PM cue means 8:30 PM; if genuinely ambiguous, set needs_clarification=true and ask rather than guessing.
- If only a start time is given with no duration, default to a 1-hour event.
- For relative dates ("next Tuesday", "this Friday"), compute precisely from the current date given above — never guess.
- Keep titles concise; move extra detail into the notes field.
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
        tools=[CREATE_EVENT_TOOL],
        tool_choice={"type": "function", "function": {"name": "create_event"}},
        max_tokens=500,
    )

    message = response.choices[0].message
    if message.tool_calls:
        args = json.loads(message.tool_calls[0].function.arguments)
        return jsonify(args)

    return jsonify({"error": "Could not parse event", "raw": message.content}), 400

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
                            "text": "Extract all course timetable slots and map them to their corresponding full names from the legend/labels in the screenshot. Return the structured slots data."
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
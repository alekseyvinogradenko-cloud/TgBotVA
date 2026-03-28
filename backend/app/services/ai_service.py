"""
AI service — parses free-text input into structured task data using GPT.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)

PARSE_TASK_PROMPT = """
You are a task parsing assistant. Extract task information from user input.
Today's date: {today}

Return a JSON object with these fields (omit if not mentioned):
- title: string (required, concise task title)
- description: string (optional, extra context)
- due_date: ISO 8601 datetime string (optional, infer from relative dates like "tomorrow", "friday")
- priority: "low" | "medium" | "high" | "urgent" (default: "medium")
- project_hint: string (optional, project name hint if mentioned)

Input: {user_input}

Respond ONLY with valid JSON, no markdown.
"""


async def parse_task_from_text(
    user_input: str,
    model: str = None,
) -> dict:
    """Parse free text into a structured task dict."""
    model = model or settings.openai_model
    today = datetime.now().strftime("%Y-%m-%d %A")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": PARSE_TASK_PROMPT.format(
                        today=today, user_input=user_input
                    ),
                }
            ],
            temperature=0.1,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"AI parse error: {e}")
        # Fallback — return raw text as title
        return {"title": user_input, "priority": "medium"}


PRIORITIZE_PROMPT = """
You are a productivity assistant. Given a list of tasks, suggest an optimized order and flag any that need attention.
Today: {today}

Tasks (JSON):
{tasks_json}

Return JSON array with same tasks, each with added:
- suggested_order: integer (1 = highest priority)
- attention_flag: boolean (true if overdue or urgent)
- note: string (optional short tip)

Respond ONLY with valid JSON array.
"""


async def prioritize_tasks(tasks: list[dict], model: str = None) -> list[dict]:
    """AI-powered task prioritization."""
    model = model or settings.openai_model
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": PRIORITIZE_PROMPT.format(
                        today=today,
                        tasks_json=json.dumps(tasks, ensure_ascii=False, default=str),
                    ),
                }
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"AI prioritize error: {e}")
        return tasks

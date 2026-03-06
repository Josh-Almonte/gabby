from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = raw_text[start : end + 1]
    candidate = (
        candidate.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def fallback_downstream_from_summary(summary_text: str) -> dict[str, Any]:
    lines = [line.strip("-• ").strip() for line in summary_text.splitlines() if line.strip()]
    if not lines:
        return {
            "overview": "",
            "decisions": [],
            "action_items": [],
            "risks": [],
            "open_questions": [],
            "follow_ups": [],
        }

    decisions = [line for line in lines if re.search(r"\b(decided|decision)\b", line, re.I)]
    action_items = [line for line in lines if re.search(r"\b(action|todo|owner|next step)\b", line, re.I)]
    risks = [line for line in lines if re.search(r"\b(risk|blocker|concern)\b", line, re.I)]
    open_questions = [line for line in lines if re.search(r"\b(question|unknown|open)\b", line, re.I)]

    return {
        "overview": lines[0],
        "decisions": decisions,
        "action_items": [{"owner": None, "task": item, "due_date": None} for item in action_items],
        "risks": risks,
        "open_questions": open_questions,
        "follow_ups": [],
    }

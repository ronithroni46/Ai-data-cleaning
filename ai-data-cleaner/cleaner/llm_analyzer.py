"""
llm_analyzer.py
Sends a data profile to Gemini and gets back structured cleaning suggestions.

Uses Google's free-tier Gemini API (Google AI Studio) instead of the
Anthropic API. Get a free key at https://aistudio.google.com/apikey
(no billing required for the free tier, but it is rate-limited).
"""
from __future__ import annotations

import json
import os
import re

from google import genai
from google.genai import types

MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """You are a meticulous data cleaning assistant.
You will be given a JSON profile of a tabular dataset (column stats, missing
values, outliers, sample rows) -- not the full dataset.

Identify concrete data quality issues and propose a specific, safe fix for
each one. Only flag real issues you can see evidence for in the profile.

Respond with ONLY a JSON array (no prose, no markdown fences). Each item:
{
  "column": "<column name, or '__row__' for whole-row issues like duplicates>",
  "issue": "<short human-readable description of the problem>",
  "severity": "low" | "medium" | "high",
  "suggested_fix": "<short human-readable description of the fix>",
  "fix_action": {
    "type": "drop_duplicates" | "fill_missing" | "strip_whitespace"
            | "standardize_case" | "convert_dtype" | "clip_outliers"
            | "drop_column" | "rename_values" | "custom",
    "params": { }
  }
}

fix_action.params conventions by type:
- fill_missing: {"strategy": "mean"|"median"|"mode"|"constant", "value": <optional, for constant>}
- strip_whitespace: {}
- standardize_case: {"case": "lower"|"upper"|"title"}
- convert_dtype: {"to": "int"|"float"|"datetime"|"string"}
- clip_outliers: {"lower": <number>, "upper": <number>}
- drop_column: {}
- rename_values: {"mapping": {"old_value": "new_value"}}
- drop_duplicates: {}
- custom: {"description": "<what to do, since no structured action fits>"}

If there are no real issues, return [].
"""


def analyze(profile_json_text: str, api_key: str | None = None) -> list[dict]:
    """Call Gemini with the profile and return a list of issue dicts."""
    client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model=MODEL,
        contents=f"Here is the dataset profile:\n\n{profile_json_text}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=4000,
        ),
    )

    raw_text = (response.text or "").strip()

    # Be defensive: strip markdown fences if the model adds them anyway
    raw_text = re.sub(r"^```(json)?", "", raw_text.strip())
    raw_text = re.sub(r"```$", "", raw_text.strip())

    try:
        issues = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse LLM response as JSON: {e}\nRaw response:\n{raw_text}"
        ) from e

    if not isinstance(issues, list):
        raise ValueError("Expected a JSON array of issues from the LLM.")

    return issues

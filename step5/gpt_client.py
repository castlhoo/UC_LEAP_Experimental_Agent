"""
Step 5 - GPT Client
=====================
GPT integration for Step 5:
  - Dataset summary generation (1st GPT call)
  - Research task generation (2nd GPT call)
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found in .env")
        _client = OpenAI(api_key=api_key)
    return _client


def call_gpt(
    prompt: str,
    system_prompt: str = "",
    model: str = "gpt-5.4",
    temperature: float = 0.2,
    max_tokens: int = 4000,
) -> str:
    """Call GPT and return raw text response."""
    client = _get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
    )

    text = resp.choices[0].message.content
    if not text:
        raise ValueError("GPT returned empty response")
    return text.strip()


def call_gpt_json(
    prompt: str,
    system_prompt: str = "",
    model: str = "gpt-5.4",
    temperature: float = 0.2,
    max_tokens: int = 4000,
) -> Dict[str, Any]:
    """Call GPT and parse JSON response."""
    client = _get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        response_format={"type": "json_object"},
    )

    text = resp.choices[0].message.content
    if not text:
        raise ValueError("GPT returned empty response")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)

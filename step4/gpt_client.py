"""
Step 4 GPT utilities.

Prompt text lives in step4/prompts so the Step 4 sub-phases are not hidden
inside this client module.
"""

from pathlib import Path
from string import Template
from typing import Any

from step3.gpt_client import call_gpt_json


CLASSIFY_SYSTEM = """You are an expert in condensed matter physics and materials science datasets.
Your task is to classify dataset files into Type 1 and Type 2 based on BOTH paper evidence and file evidence.
You must follow a structured reasoning process and be precise, conservative, and evidence-based. Return structured JSON."""

STEP4_DIR = Path(__file__).resolve().parent


def load_prompt(filename: str) -> str:
    """Load a Step 4 prompt template by path relative to step4/."""
    return (STEP4_DIR / filename).read_text(encoding="utf-8")


def render_prompt(filename: str, **kwargs: Any) -> str:
    """Render a prompt template without requiring JSON braces to be escaped."""
    values = {key: "" if value is None else str(value) for key, value in kwargs.items()}
    return Template(load_prompt(filename)).safe_substitute(values)

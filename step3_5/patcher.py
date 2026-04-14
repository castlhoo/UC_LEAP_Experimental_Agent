"""Patch scripts with minimal execution-only changes."""

import json
from pathlib import Path
from typing import Any, Dict

from step3_5.prompt_client import prompt_enabled, run_patch_prompt


def patch_execution_target(paper: Dict[str, Any], preparation: Dict[str, Any], bundle_dir: str, output_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    target_rel = preparation.get("execution_target_script", "")
    if not target_rel:
        return {
            "should_patch": False,
            "patch_summary": "No execution target script was identified.",
            "path_fixes": [],
            "output_saves_added": [],
            "entrypoint_changes": [],
            "patched_script_path": "",
            "expected_generated_files": [],
            "figure_hints": ["unknown"],
            "risks": ["no_target_script"],
            "confidence": "low",
        }

    script_path = Path(bundle_dir) / target_rel
    if not script_path.exists():
        return {
            "should_patch": False,
            "patch_summary": "Target script missing from bundle.",
            "path_fixes": [],
            "output_saves_added": [],
            "entrypoint_changes": [],
            "patched_script_path": "",
            "expected_generated_files": [],
            "figure_hints": preparation.get("figure_hints", ["unknown"]),
            "risks": ["target_script_missing"],
            "confidence": "low",
        }

    original_text = script_path.read_text(encoding="utf-8", errors="ignore")
    result = None
    if prompt_enabled(config):
        try:
            payload = {
                "title": paper.get("title", ""),
                "execution_preparation": json.dumps(preparation, indent=2, ensure_ascii=False)[:6000],
                "script_path": str(script_path),
                "script_content": original_text[:12000],
                "type2_files": json.dumps([fc for fc in paper.get("file_classifications", []) if fc.get("type") == "type2"], indent=2, ensure_ascii=False)[:6000],
                "workdir": bundle_dir,
                "output_dir": output_dir,
            }
            result = run_patch_prompt(payload, config)
        except Exception:
            result = None

    if not result:
        result = {
            "should_patch": False,
            "patch_summary": "Original script used without GPT patch.",
            "path_fixes": [],
            "output_saves_added": [],
            "entrypoint_changes": [],
            "patched_script": original_text,
            "expected_generated_files": [],
            "figure_hints": preparation.get("figure_hints", ["unknown"]),
            "risks": ["no_patch_applied"],
            "confidence": "low",
        }

    patched_text = result.get("patched_script") or original_text
    script_path.write_text(patched_text, encoding="utf-8")
    result["patched_script_path"] = str(script_path)
    return result

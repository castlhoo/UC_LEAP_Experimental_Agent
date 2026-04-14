"""Evaluate execution results and decide whether a paper becomes Both via script."""

import json
from pathlib import Path
from typing import Any, Dict, List

from step3_5.prompt_client import prompt_enabled, run_evaluation_prompt


def evaluate_execution(paper: Dict[str, Any], preparation: Dict[str, Any], patch_result: Dict[str, Any], execution_result: Dict[str, Any], bundle_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    generated_outputs = _summarize_outputs(bundle_dir, execution_result.get("generated_files", []))

    if prompt_enabled(config):
        try:
            payload = {
                "title": paper.get("title", ""),
                "journal": paper.get("journal", ""),
                "paper_analysis": json.dumps(paper.get("paper_analysis", {}), indent=2, ensure_ascii=False)[:8000],
                "type2_files": json.dumps([fc for fc in paper.get("file_classifications", []) if fc.get("type") == "type2"], indent=2, ensure_ascii=False)[:6000],
                "script_files": json.dumps([fc for fc in paper.get("file_classifications", []) if fc.get("type") == "script"], indent=2, ensure_ascii=False)[:4000],
                "execution_preparation": json.dumps(preparation, indent=2, ensure_ascii=False)[:6000],
                "patch_summary": json.dumps(patch_result, indent=2, ensure_ascii=False)[:6000],
                "execution_log": json.dumps({k: execution_result.get(k, "") for k in ("status", "stdout", "stderr")}, indent=2, ensure_ascii=False)[:12000],
                "generated_outputs": json.dumps(generated_outputs, indent=2, ensure_ascii=False)[:4000],
            }
            return run_evaluation_prompt(payload, config)
        except Exception:
            pass

    reusable_exts = set(config.get("outputs", {}).get("reusable_extensions", []))
    image_exts = set(config.get("outputs", {}).get("image_only_extensions", []))
    reusable = [g["relative_path"] for g in generated_outputs if g["extension"] in reusable_exts]
    images = [g["relative_path"] for g in generated_outputs if g["extension"] in image_exts]
    exec_ok = bool(execution_result.get("success"))
    # Heuristic: reusable numeric data → Both. Image-only → conservatively no
    # (GPT prompt path handles image-only with type2 verification)
    count_both = exec_ok and bool(reusable)
    all_type1_files = reusable if reusable else images
    if reusable and images:
        kind = "mixed"
    elif reusable:
        kind = "csv / xlsx / txt / npy"
    elif images:
        kind = "figure image only"
    else:
        kind = "unclear"
    evidence_for = []
    if reusable:
        evidence_for.append("Reusable numeric outputs were generated.")
    if images and not reusable:
        evidence_for.append("Figure images generated, but heuristic cannot verify type2 data linkage.")
    return {
        "execution_successful": exec_ok,
        "execution_status": execution_result.get("status", "unclear_output"),
        "generated_type1_data": bool(reusable),
        "count_paper_as_both": count_both,
        "generated_type1_files": all_type1_files,
        "generated_output_kind": kind,
        "figure_mapping": [{"output_file": path, "figure": "unknown", "confidence": "low"} for path in all_type1_files[:10]],
        "evidence_for": evidence_for,
        "evidence_against": ["Only figure images produced; cannot verify type2 linkage without GPT."] if images and not reusable else ([] if reusable else ["No outputs were generated."]),
        "type1_generation_summary": "Heuristic evaluation used because GPT was unavailable or disabled.",
        "confidence": "medium" if reusable else "low",
        "reasoning": "Counted as Both — reusable numeric data generated." if count_both else "Heuristic could not confirm Both without reusable numeric outputs.",
    }


def _summarize_outputs(bundle_dir: str, generated_files: List[str]) -> List[Dict[str, Any]]:
    summaries = []
    base = Path(bundle_dir)
    for rel in generated_files:
        path = base / rel
        if not path.exists() or not path.is_file():
            continue
        summaries.append({
            "relative_path": rel.replace("\\", "/"),
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        })
    return summaries

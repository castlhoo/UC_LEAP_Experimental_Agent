"""Candidate selection and execution preparation helpers."""

import json
from pathlib import Path
from typing import Any, Dict, List

TEXT_SCRIPT_EXTS = {".py", ".ipynb", ".m", ".r", ".jl", ".sh", ".c", ".cpp"}
SCRIPT_NAME_HINTS = ("fig", "plot", "analy", "process", "make", "render")


def select_candidates(step3_data: Dict[str, Any], max_papers: int | None = None) -> List[Dict[str, Any]]:
    papers = []
    for paper in step3_data.get("all_papers", []):
        if not paper.get("has_type2"):
            continue
        scripts = [fc for fc in paper.get("file_classifications", []) if fc.get("type") == "script"]
        if not scripts:
            continue
        paper = dict(paper)
        paper["script_candidates"] = scripts
        papers.append(paper)
    return papers if max_papers in (None, 0) else papers[:max_papers]


def summarize_file_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "relative_path": entry.get("relative_path", ""),
        "filename": entry.get("filename", ""),
        "type": entry.get("type", ""),
        "file_evidence": entry.get("file_evidence", ""),
        "reasoning": entry.get("reasoning", ""),
        "key_columns_or_structure": entry.get("key_columns_or_structure", ""),
    }


def gather_type2_files(paper: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [summarize_file_entry(fc) for fc in paper.get("file_classifications", []) if fc.get("type") == "type2"]


def gather_script_files(paper: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [summarize_file_entry(fc) for fc in paper.get("file_classifications", []) if fc.get("type") == "script"]


def infer_script_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".ipynb": "notebook",
        ".m": "matlab",
        ".r": "r",
        ".jl": "julia",
    }.get(ext, "unknown")


def choose_default_script(script_files: List[Dict[str, Any]]) -> str:
    if not script_files:
        return ""
    ranked = sorted(
        script_files,
        key=lambda x: (
            0 if any(h in (x.get("filename", "").lower()) for h in SCRIPT_NAME_HINTS) else 1,
            0 if Path(x.get("filename", "")).suffix.lower() in {".py", ".ipynb"} else 1,
            len(x.get("relative_path", "") or x.get("filename", "")),
        ),
    )
    return ranked[0].get("relative_path") or ranked[0].get("filename", "")


def load_script_texts(download_dir: str, script_files: List[Dict[str, Any]], max_chars: int = 4000) -> List[Dict[str, Any]]:
    summaries = []
    for sf in script_files:
        rel = sf.get("relative_path") or sf.get("filename", "")
        path = Path(download_dir) / rel
        ext = path.suffix.lower()
        if ext not in TEXT_SCRIPT_EXTS or not path.exists():
            summaries.append({"relative_path": rel, "content_preview": "", "readable": False})
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        summaries.append({"relative_path": rel, "content_preview": text[:max_chars], "readable": True})
    return summaries


def preparation_payload(paper: Dict[str, Any]) -> Dict[str, str]:
    type2_files = gather_type2_files(paper)
    script_files = gather_script_files(paper)
    script_summaries = load_script_texts(paper.get("download_dir", ""), script_files)
    return {
        "title": paper.get("title", ""),
        "journal": paper.get("journal", ""),
        "abstract": paper.get("paper_analysis", {}).get("summary", ""),
        "paper_analysis": json.dumps(paper.get("paper_analysis", {}), indent=2, ensure_ascii=False)[:8000],
        "type2_files": json.dumps(type2_files, indent=2, ensure_ascii=False)[:6000],
        "script_files": json.dumps(script_files, indent=2, ensure_ascii=False)[:4000],
        "script_summaries": json.dumps(script_summaries, indent=2, ensure_ascii=False)[:8000],
    }


def heuristic_preparation(paper: Dict[str, Any]) -> Dict[str, Any]:
    type2_files = gather_type2_files(paper)
    script_files = gather_script_files(paper)
    target = choose_default_script(script_files)
    language = infer_script_language(target)
    dependency_hints = []
    for summary in load_script_texts(paper.get("download_dir", ""), script_files):
        preview = summary.get("content_preview", "")
        for token in ("numpy", "pandas", "matplotlib", "scipy", "h5py"):
            if token in preview and token not in dependency_hints:
                dependency_hints.append(token)
    return {
        "execution_target_script": target,
        "script_language": language,
        "likely_input_files": [x.get("relative_path", "") for x in type2_files[:10]],
        "likely_output_files": [],
        "expected_output_kind": "mixed" if target else "unclear",
        "path_issues": ["relative path mismatch possible"],
        "dependency_hints": dependency_hints,
        "entrypoint_status": "clear" if language in {"python", "notebook"} else "unclear",
        "figure_hints": ["unknown"],
        "preparation_summary": "Heuristic preparation used because GPT was unavailable or disabled.",
        "confidence": "low" if not target else "medium",
    }

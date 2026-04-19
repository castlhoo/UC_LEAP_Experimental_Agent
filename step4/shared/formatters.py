"""Prompt-formatting helpers shared by Step 4 phases."""

from typing import Any, Dict, List, Optional


def format_paper_analysis(analysis: Optional[Dict[str, Any]], include_figures: bool = True) -> str:
    if not analysis or not analysis.get("summary"):
        return "(Paper analysis not available - classify based on file inspection only)"

    lines = [f"Summary: {analysis.get('summary', '')}"]
    mtypes = analysis.get("measurement_types", [])
    if mtypes:
        lines.append(f"Measurement types: {', '.join(mtypes)}")
    if analysis.get("has_raw_measurements"):
        lines.append(f"Raw measurements: {analysis.get('raw_measurement_details', '')}")

    dataset_char = analysis.get("dataset_characterization", {}) or {}
    if dataset_char.get("data_availability_statement"):
        lines.append(f"Data availability: {dataset_char.get('data_availability_statement', '')}")
    provided_types = dataset_char.get("data_provided_types", [])
    if provided_types:
        lines.append(f"Data provided types: {', '.join(provided_types)}")

    prior = analysis.get("classification_prior", {}) or {}
    if prior:
        lines.append("Classification prior:")
        lines.append(f"  raw_data_expected: {prior.get('raw_data_expected', False)}")
        lines.append(f"  source_data_expected: {prior.get('source_data_expected', False)}")
        if prior.get("raw_data_evidence"):
            lines.append(f"  raw_data_evidence: {prior.get('raw_data_evidence', '')}")
        if prior.get("source_data_evidence"):
            lines.append(f"  source_data_evidence: {prior.get('source_data_evidence', '')}")
        if prior.get("priority_modalities"):
            lines.append(f"  priority_modalities: {', '.join(prior.get('priority_modalities', []))}")

    figures = analysis.get("figures", [])
    if figures:
        lines.append(f"\nFigures ({len(figures)}):")
        shown_figures = figures if include_figures else figures[:8]
        for fig in shown_figures:
            lines.append(
                f"  {fig.get('figure_id', '?')}: {fig.get('description', '?')} "
                f"[{fig.get('data_type', '?')}] (source: {fig.get('likely_source', '?')})"
            )
        if not include_figures and len(figures) > len(shown_figures):
            lines.append(f"  ... {len(figures) - len(shown_figures)} additional figures omitted for this phase")
    return "\n".join(lines)


def format_discovery_evidence(paper: Dict[str, Any]) -> str:
    """Format Step 1/2 evidence so Prompt B can use the full provenance chain."""
    lines = []

    lines.append("Step 1 screening:")
    lines.append(f"  decision: {paper.get('screening_decision', '')}")
    if paper.get("verification_reasons"):
        lines.append("  step2_verification_reasons:")
        for reason in paper.get("verification_reasons", [])[:8]:
            lines.append(f"    - {reason}")
    if paper.get("needs_human_review"):
        lines.append("  needs_human_review: true")

    lines.append("\nStep 2 link routing:")
    lines.append(f"  dataset_status: {paper.get('dataset_status', '')}")

    pdf_urls = paper.get("paper_pdf_urls", [])
    if pdf_urls:
        lines.append(f"  paper_pdf_urls ({len(pdf_urls)}):")
        for item in pdf_urls[:5]:
            if isinstance(item, dict):
                lines.append(
                    f"    - {item.get('url', '')} "
                    f"[source={item.get('source', '?')}; validated={item.get('validated', False)}]"
                )
            else:
                lines.append(f"    - {item}")
    if paper.get("resolved_paper_pdf_url"):
        lines.append(
            "  resolved_paper_pdf_url: "
            f"{paper.get('resolved_paper_pdf_url')} "
            f"[source={paper.get('paper_pdf_source', '')}]"
        )

    data_candidates = paper.get("data_url_candidates", paper.get("source_data_files", []))
    if data_candidates:
        lines.append(f"  data_url_candidates ({len(data_candidates)}):")
        for item in data_candidates[:12]:
            lines.append(
                "    - "
                f"{item.get('filename') or item.get('url', '')} "
                f"[source={item.get('source', '?')}; reason={item.get('reason', '?')}] "
                f"{item.get('url', '')}"
            )

    repo_urls = paper.get("repository_urls", [])
    if repo_urls:
        lines.append(f"  repository_urls ({len(repo_urls)}):")
        for url in repo_urls[:8]:
            lines.append(f"    - {url}")

    ambiguous = paper.get("ambiguous_url_candidates", [])
    if ambiguous:
        lines.append(f"  ambiguous_url_candidates ({len(ambiguous)}; preserved non-junk unresolved URLs):")
        for item in ambiguous[:8]:
            lines.append(
                "    - "
                f"{item.get('filename') or item.get('url', '')} "
                f"[source={item.get('source', '?')}; reason={item.get('reason', '?')}] "
                f"{item.get('url', '')}"
            )

    repos = paper.get("repositories", [])
    if repos:
        lines.append(f"  repository_inventories ({len(repos)}):")
        for repo in repos[:8]:
            inv = repo.get("inventory", {})
            lines.append(
                f"    - {repo.get('repo_type', '?')} {repo.get('url', '')} "
                f"inventory_success={inv.get('success', False)} "
                f"file_count={inv.get('file_count', 0)}"
            )
            files = inv.get("files", []) if inv.get("success") else []
            for f in files[:8]:
                lines.append(
                    "      * "
                    f"{f.get('filename', '?')} "
                    f"ext={f.get('extension', '')} size={f.get('size_human', '')}"
                )

    da_text = paper.get("data_availability_text", "")
    if da_text:
        lines.append("\nStep 2 data availability text:")
        lines.append(f"  {da_text[:1200]}")

    ignored = paper.get("ignored_urls", [])
    if ignored:
        lines.append(f"\nIgnored non-data/site URLs ({len(ignored)}; not evidence for data type):")
        for item in ignored[:8]:
            lines.append(f"  - {item.get('filename') or item.get('url', '')}: {item.get('reason', '')}")

    return "\n".join(lines)


def format_dataset_assessment(assessment: Dict[str, Any]) -> str:
    if not assessment:
        return "(Dataset-level assessment not available)"
    lines = [
        f"Dataset overview: {assessment.get('dataset_overview', '')}",
        f"Paper-dataset link: {assessment.get('paper_dataset_link', '')}",
        f"Scientific context: {assessment.get('scientific_context', '')}",
        f"Data contents summary: {assessment.get('data_contents_summary', '')}",
        f"Data modalities: {', '.join(assessment.get('data_modalities', []) or [])}",
        f"Data generation/processing: {assessment.get('data_generation_or_processing', '')}",
        f"field_match: {assessment.get('field_match', '')}",
        f"field_match_reasoning: {assessment.get('field_match_reasoning', '')}",
        f"likely_dataset_structure: {assessment.get('likely_dataset_structure', '')}",
        f"out_of_scope: {assessment.get('out_of_scope', False)}",
        f"out_of_scope_reason: {assessment.get('out_of_scope_reason', '')}",
    ]
    plan = assessment.get("type_classification_plan", {}) or {}
    if plan:
        lines.append("Type classification plan:")
        lines.append(f"  likely_type1_evidence: {plan.get('likely_type1_evidence', '')}")
        lines.append(f"  likely_type2_evidence: {plan.get('likely_type2_evidence', '')}")
        if plan.get("files_or_groups_to_prioritize"):
            lines.append(
                "  files_or_groups_to_prioritize: "
                + ", ".join(plan.get("files_or_groups_to_prioritize", []))
            )
    if assessment.get("notes"):
        lines.append(f"Notes: {assessment.get('notes', '')}")
    return "\n".join(lines)


def format_file_overview(file_reports: List[Dict[str, Any]], max_files: int = 80) -> str:
    type_counts: Dict[str, int] = {}
    lines = []
    for report in file_reports:
        ftype = report.get("file_type", "unknown")
        type_counts[ftype] = type_counts.get(ftype, 0) + 1
    lines.append(f"Total inspected files: {len(file_reports)}")
    lines.append(f"File type counts: {type_counts}")

    for i, report in enumerate(file_reports[:max_files], start=1):
        name = report.get("relative_path") or report.get("filename", "?")
        parts = [
            f"{i}. {name}",
            f"type={report.get('file_type', '?')}",
            f"size={report.get('size_human', '?')}",
        ]
        if report.get("columns"):
            parts.append(f"columns={report.get('columns', [])[:15]}")
            parts.append(f"rows={report.get('row_count', '?')}")
        if report.get("sheet_names"):
            parts.append(f"sheets={report.get('sheet_names', [])[:10]}")
        if report.get("groups"):
            parts.append(f"hdf5_groups={report.get('groups', [])[:10]}")
        if report.get("datasets"):
            ds = report.get("datasets", [])[:8]
            parts.append(
                "hdf5_datasets="
                + str([
                    {
                        "path": d.get("path", ""),
                        "shape": d.get("shape", ""),
                        "dtype": d.get("dtype", ""),
                    }
                    for d in ds
                ])
            )
        if report.get("keys"):
            parts.append(f"json_keys={report.get('keys', [])[:15]}")
        if report.get("note"):
            parts.append(f"note={report.get('note', '')}")
        if report.get("error"):
            parts.append(f"error={report.get('error', '')}")
        lines.append(" | ".join(parts))

    if len(file_reports) > max_files:
        lines.append(f"... {len(file_reports) - max_files} additional files omitted from overview")
    return "\n".join(lines)


def format_file_reports(reports: List[Dict[str, Any]]) -> str:
    parts = []
    for i, r in enumerate(reports[:30]):
        display_name = r.get("relative_path") or r.get("filename", "?")
        lines = [f"--- File {i+1}: {display_name} ---"]
        if r.get("relative_path"):
            lines.append(f"  Relative path: {r['relative_path']}")
        lines.append(f"  Type: {r.get('file_type', '?')}")
        lines.append(f"  Size: {r.get('size_human', '?')}")
        lines.append(f"  Source: {r.get('download_source', '?')}")
        if r.get("from_zip"):
            lines.append(f"  Extracted from ZIP: {r['from_zip']}")
        if r.get("error"):
            lines.append(f"  Error: {r['error']}")
        if r.get("file_type") == "tabular_text":
            lines.append(f"  Columns ({r.get('column_count', '?')}): {r.get('columns', [])}")
            lines.append(f"  Rows: {r.get('row_count', '?')}")
            lines.append(f"  Has header: {r.get('has_header', '?')}")
            lines.append(f"  Has numeric: {r.get('has_numeric_data', '?')}")
            lines.append(f"  Dtypes: {r.get('dtypes', {})}")
            if r.get("sample_rows"):
                lines.append(f"  Sample row: {r['sample_rows'][0]}")
        elif r.get("file_type") == "excel":
            lines.append(f"  Sheets ({r.get('sheet_count', '?')}): {r.get('sheet_names', [])[:10]}")
            for sheet in r.get("sheets", [])[:5]:
                if sheet.get("error"):
                    lines.append(f"    Sheet '{sheet.get('sheet_name','?')}': ERROR {sheet['error'][:80]}")
                    continue
                cols = sheet.get("named_columns") or sheet.get("columns", [])
                lines.append(
                    f"    Sheet '{sheet.get('sheet_name','?')}': "
                    f"{sheet.get('column_count', '?')} cols x {sheet.get('row_count', '?')} rows"
                )
                lines.append(f"    Key columns: {cols[:15]}")
                lines.append(f"    Has header: {sheet.get('has_header', '?')}")
        elif r.get("file_type") == "hdf5":
            lines.append(f"  Groups ({r.get('group_count', '?')}): {r.get('groups', [])[:10]}")
            for ds in r.get("datasets", [])[:10]:
                lines.append(f"    {ds['path']}: shape={ds['shape']}, dtype={ds['dtype']}")
        elif r.get("file_type") == "json":
            lines.append(f"  Structure: {r.get('structure', '?')}")
            if r.get("keys"):
                lines.append(f"  Keys: {r['keys']}")
        elif r.get("file_type") == "numpy":
            if r.get("arrays"):
                for k, v in r["arrays"].items():
                    lines.append(f"  Array '{k}': shape={v.get('shape')}, dtype={v.get('dtype')}")
            elif r.get("shape"):
                lines.append(f"  Shape: {r['shape']}, dtype: {r.get('dtype')}")
        elif r.get("file_type") in ("microscopy_image", "optical_image", "instrument_raw", "script", "documentation", "pdf"):
            if r.get("note"):
                lines.append(f"  Note: {r['note']}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def brief_structure(report: Dict[str, Any]) -> str:
    if report.get("columns"):
        return ", ".join(str(c) for c in report.get("columns", [])[:10])
    if report.get("sheet_names"):
        return "sheets: " + ", ".join(str(s) for s in report.get("sheet_names", [])[:10])
    if report.get("groups"):
        return "groups: " + ", ".join(str(g) for g in report.get("groups", [])[:10])
    if report.get("keys"):
        return "keys: " + ", ".join(str(k) for k in report.get("keys", [])[:10])
    return report.get("note", "")

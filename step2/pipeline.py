"""
Step 2 - Pipeline
===================
Orchestrates Dataset Presence and Inventory Check:
  Phase 1: Load Step 1 candidates
  Phase 2: Resolve dataset links (CrossRef, DOI landing pages)
  Phase 3: Classify repositories (Zenodo, Figshare, GitHub, Dryad, etc.)
  Phase 4: Collect file inventories via repository APIs
  Phase 5: GPT assessment of inventories
  Phase 6: Save results
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

import yaml

from step2.candidate_loader import load_candidates
from step2.dataset_link_resolver import resolve_dataset_links
from step2.repository_classifier import classify_all_links, classify_url, classify_doi
from step2.inventory_collector import collect_inventory
from step2.gpt_client import gpt_assess_inventory, call_gpt_json

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load Step 2 configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "step2_config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_step2() -> Dict[str, Any]:
    """
    Execute the full Step 2 pipeline.

    Returns:
        Summary dict with statistics and output file path.
    """
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    gpt_config = config.get("gpt", {})
    use_gpt = gpt_config.get("enabled", False)
    gpt_model = gpt_config.get("model", "gpt-5.4-mini")

    http_config = config.get("http", {})
    rate_limit_delay = http_config.get("rate_limit_delay", 1.0)

    # ---- Phase 1: Load candidates ----
    logger.info("=" * 60)
    logger.info("Phase 1: Loading Step 1 candidates...")

    input_path = os.path.join(project_root, config.get("input_file", ""))
    include_decisions = config.get("include_decisions", ["keep", "maybe"])
    candidates = load_candidates(input_path, include_decisions)

    if not candidates:
        logger.warning("No candidates to process!")
        return {"status": "empty", "candidates_processed": 0}

    logger.info(f"Loaded {len(candidates)} candidates for processing")

    # ---- Phase 2 & 3: Resolve links + Classify repositories ----
    logger.info("=" * 60)
    logger.info("Phase 2-3: Resolving dataset links & classifying repositories...")

    results = []
    papers_with_repos = 0
    total_repos_found = 0

    for i, paper in enumerate(candidates):
        if (i + 1) % 10 == 1 or (i + 1) == len(candidates):
            logger.info(f"  Resolving links for paper {i + 1}/{len(candidates)}...")

        title = paper.get("title", "")[:60]

        # Phase 2: Resolve dataset links
        link_result = resolve_dataset_links(
            paper, http_config, rate_limit_delay,
            use_gpt=use_gpt,
            gpt_call_fn=call_gpt_json if use_gpt else None,
            gpt_model=gpt_model,
        )
        discovered_urls = link_result.get("discovered_urls", [])

        # Phase 3: Classify all discovered URLs
        # First, classify URLs already in the paper from Step 1
        classified_repos = classify_all_links(paper)

        # Then classify newly discovered URLs
        for url in discovered_urls:
            classified = classify_url(url)
            if classified:
                # Deduplicate
                key = (classified["repo_type"], classified["repo_id"])
                existing_keys = {
                    (r["repo_type"], r["repo_id"]) for r in classified_repos
                }
                if key not in existing_keys:
                    classified_repos.append(classified)

            # Also try DOI-based classification
            # Extract DOI from URL if it's a doi.org URL
            if "doi.org/" in url:
                doi_part = url.split("doi.org/")[-1]
                doi_classified = classify_doi(doi_part)
                if doi_classified:
                    key = (doi_classified["repo_type"], doi_classified["repo_id"])
                    existing_keys = {
                        (r["repo_type"], r["repo_id"]) for r in classified_repos
                    }
                    if key not in existing_keys:
                        classified_repos.append(doi_classified)

        if classified_repos:
            papers_with_repos += 1
            total_repos_found += len(classified_repos)

        # Log what we found
        n_urls = len(discovered_urls)
        n_source = len(link_result.get("source_data_files", []))
        da_text = link_result.get("data_availability_text", "")
        gpt_loc = link_result.get("gpt_analysis", {}).get("dataset_location", "")
        if n_urls > 0 or n_source > 0:
            logger.info(
                f"    -> {title}: {n_urls} URLs, {n_source} source files, "
                f"DA={'yes' if da_text else 'no'}, GPT={gpt_loc or 'n/a'}"
            )

        results.append({
            "paper": paper,
            "link_resolution": link_result,
            "classified_repos": classified_repos,
            "inventories": [],
            "assessments": [],
        })

    logger.info(
        f"  Found repositories for {papers_with_repos}/{len(candidates)} papers "
        f"({total_repos_found} total repos)"
    )

    # ---- Phase 4: Collect inventories ----
    logger.info("=" * 60)
    logger.info("Phase 4: Collecting file inventories from repositories...")

    inventory_success = 0
    inventory_fail = 0

    for i, entry in enumerate(results):
        repos = entry["classified_repos"]
        if not repos:
            continue

        title = entry["paper"].get("title", "")[:50]
        logger.info(f"  [{i + 1}] {title}... ({len(repos)} repos)")

        for repo in repos:
            time.sleep(rate_limit_delay)
            inventory = collect_inventory(repo, http_config)

            if inventory.get("success"):
                inventory_success += 1
                file_count = inventory.get("file_count", 0)
                total_size = inventory.get("total_size_human", "?")
                logger.info(
                    f"    ✓ {repo['repo_type']}: {file_count} files, {total_size}"
                )
            else:
                inventory_fail += 1
                error = inventory.get("error", "unknown")
                logger.info(f"    ✗ {repo['repo_type']}: {error}")

            entry["inventories"].append(inventory)

    logger.info(
        f"  Inventory results: {inventory_success} success, {inventory_fail} failed"
    )

    # ---- Phase 5: GPT assessment ----
    if use_gpt:
        logger.info("=" * 60)
        logger.info("Phase 5: GPT inventory & source data assessment...")

        assessed = 0
        for entry in results:
            # Assess repo inventories (Zenodo, Figshare, etc.)
            for inv in entry["inventories"]:
                if inv.get("success") and inv.get("file_count", 0) > 0:
                    assessment = gpt_assess_inventory(
                        entry["paper"], inv, model=gpt_model
                    )
                    entry["assessments"].append(assessment)
                    assessed += 1

            # Assess publisher source data files (if no repo inventory)
            if not entry["assessments"]:
                source_files = entry["link_resolution"].get("source_data_files", [])
                if source_files:
                    # Build a pseudo-inventory from source data files
                    pseudo_inv = {
                        "repo_type": "publisher_source_data",
                        "title": entry["paper"].get("title", ""),
                        "description": entry["link_resolution"].get(
                            "gpt_analysis", {}
                        ).get("data_description", ""),
                        "files": [
                            {
                                "filename": f.get("filename", "unknown"),
                                "size_human": "unknown",
                                "extension": f.get("filename", "").rsplit(".", 1)[-1].lower()
                                    if "." in f.get("filename", "") else "",
                            }
                            for f in source_files
                        ],
                    }
                    assessment = gpt_assess_inventory(
                        entry["paper"], pseudo_inv, model=gpt_model
                    )
                    entry["assessments"].append(assessment)
                    assessed += 1

        logger.info(f"  Assessed {assessed} papers with GPT")
    else:
        logger.info("Phase 5: Skipped (GPT disabled)")

    # ---- Phase 6: Save results ----
    logger.info("=" * 60)
    logger.info("Phase 6: Saving results...")

    output = _build_output(results, config)
    output_dir = os.path.join(project_root, config.get("output_dir", "step2/output"))
    os.makedirs(output_dir, exist_ok=True)

    # Save timestamped file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_path = os.path.join(output_dir, f"step2_inventory_{timestamp}.json")
    latest_path = os.path.join(output_dir, "step2_inventory_latest.json")

    for path in [ts_path, latest_path]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"  Saved: {ts_path}")
    logger.info(f"  Saved: {latest_path}")

    # Print summary
    _print_summary(output)

    return {
        "status": "success",
        "candidates_processed": len(candidates),
        "papers_with_datasets": output["summary"]["papers_with_verified_repos"],
        "output_file": latest_path,
    }


def _build_output(results: List[Dict], config: Dict) -> Dict[str, Any]:
    """Build the final output JSON structure."""
    papers = []
    papers_with_repos = 0
    papers_with_inventories = 0
    total_files = 0
    repo_type_counts = {}

    for entry in results:
        paper = entry["paper"]
        repos = entry["classified_repos"]
        inventories = entry["inventories"]
        assessments = entry["assessments"]

        has_repo = len(repos) > 0
        successful_inventories = [inv for inv in inventories if inv.get("success")]
        has_inventory = len(successful_inventories) > 0

        if has_repo:
            papers_with_repos += 1
        if has_inventory:
            papers_with_inventories += 1

        # Build repository entries
        repo_entries = []
        for j, repo in enumerate(repos):
            inv = inventories[j] if j < len(inventories) else {}
            assess = assessments[j] if j < len(assessments) else {}

            repo_type = repo.get("repo_type", "unknown")
            repo_type_counts[repo_type] = repo_type_counts.get(repo_type, 0) + 1

            if inv.get("success"):
                total_files += inv.get("file_count", 0)

            repo_entries.append({
                "repo_type": repo_type,
                "repo_id": repo.get("repo_id", ""),
                "url": repo.get("url", ""),
                "inventory": {
                    "success": inv.get("success", False),
                    "file_count": inv.get("file_count", 0),
                    "total_size_human": inv.get("total_size_human", ""),
                    "files": inv.get("files", []),
                    "title": inv.get("title", ""),
                    "license": inv.get("license", ""),
                } if inv.get("success") else {
                    "success": False,
                    "error": inv.get("error", "not attempted"),
                },
                "assessment": assess if assess else None,
            })

        # Determine overall dataset status
        # Also consider source_data_files and GPT analysis
        link_res = entry["link_resolution"]
        has_source_files = len(link_res.get("source_data_files", [])) > 0
        da_upon_request = link_res.get("da_upon_request", False)
        gpt_analysis = link_res.get("gpt_analysis", {})
        gpt_location = gpt_analysis.get("dataset_location", "")

        if has_inventory:
            dataset_status = "verified"
        elif has_repo:
            dataset_status = "link_found"
        elif da_upon_request and not has_source_files:
            # DA explicitly says "upon request" and no real data files found
            dataset_status = "upon_request"
        elif has_source_files:
            dataset_status = "source_data_found"
        elif gpt_location in ("publisher_source_data", "supplementary", "repository"):
            dataset_status = "source_data_found"
        elif gpt_location == "upon_request" or da_upon_request:
            dataset_status = "upon_request"
        elif link_res.get("has_dataset_link"):
            dataset_status = "unclassified_link"
        else:
            dataset_status = "no_dataset_found"

        # Determine dataset_type from assessments
        dataset_type = "unknown"
        type1_evidence = "none"
        type2_evidence = "none"
        for assess in assessments:
            if isinstance(assess, dict) and assess.get("dataset_type"):
                dt = assess["dataset_type"]
                if dt in ("type1", "type2", "both"):
                    dataset_type = dt
                    type1_evidence = assess.get("type1_evidence", "none")
                    type2_evidence = assess.get("type2_evidence", "none")
                    break

        papers.append({
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "paper_url": paper.get("paper_url", ""),
            "priority_score": paper.get("priority_score", 0),
            "screening_decision": paper.get("screening_decision", ""),
            "abstract_summary": paper.get("abstract_summary", ""),
            "dataset_status": dataset_status,
            "dataset_type": dataset_type,
            "type1_evidence": type1_evidence,
            "type2_evidence": type2_evidence,
            "repositories": repo_entries,
            "source_data_files": link_res.get("source_data_files", []),
            "data_availability_text": link_res.get("data_availability_text", ""),
            "gpt_data_analysis": gpt_analysis,
            "discovered_urls": link_res.get("discovered_urls", []),
            "link_sources": link_res.get("sources", {}),
        })

    # Sort: verified first, then by priority score
    status_order = {"verified": 0, "source_data_found": 1, "link_found": 2, "unclassified_link": 3, "upon_request": 4, "no_dataset_found": 5}
    papers.sort(key=lambda x: (
        status_order.get(x["dataset_status"], 9),
        -x.get("priority_score", 0),
    ))

    # Count dataset types
    type_counts = {}
    for p in papers:
        dt = p.get("dataset_type", "unknown")
        type_counts[dt] = type_counts.get(dt, 0) + 1

    return {
        "metadata": {
            "step": 2,
            "description": "Dataset Presence, Inventory & Structure Classification",
            "generated_at": datetime.now().isoformat(),
            "total_papers": len(papers),
        },
        "summary": {
            "total_papers": len(papers),
            "dataset_status_distribution": {
                s: sum(1 for p in papers if p["dataset_status"] == s)
                for s in ["verified", "source_data_found", "link_found",
                          "unclassified_link", "upon_request", "no_dataset_found"]
                if any(p["dataset_status"] == s for p in papers)
            },
            "papers_with_verified_repos": papers_with_inventories,
            "papers_with_data": sum(
                1 for p in papers
                if p["dataset_status"] in ("verified", "source_data_found", "link_found")
            ),
            "total_files_found": total_files,
            "repo_type_distribution": repo_type_counts,
            "dataset_type_distribution": type_counts,
        },
        "papers": papers,
    }


def _print_summary(output: Dict[str, Any]):
    """Print a formatted summary to the log."""
    summary = output["summary"]
    papers = output["papers"]

    logger.info("=" * 60)
    logger.info("STEP 2 RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total papers processed:     {summary['total_papers']}")
    logger.info(f"Papers with data:           {summary['papers_with_data']}")
    logger.info(f"Status distribution:        {summary['dataset_status_distribution']}")
    logger.info(f"Total files found:          {summary['total_files_found']}")
    logger.info(f"Repository types:           {summary['repo_type_distribution']}")
    logger.info(f"Dataset type distribution:  {summary['dataset_type_distribution']}")

    # Show papers with data (verified + source_data_found + link_found)
    with_data = [
        p for p in papers
        if p["dataset_status"] in ("verified", "source_data_found", "link_found")
    ]
    if with_data:
        logger.info("-" * 60)
        logger.info("PAPERS WITH DATA:")
        for p in with_data[:15]:
            status = p["dataset_status"]
            dt = p.get("dataset_type", "unknown")
            gpt_loc = p.get("gpt_data_analysis", {}).get("dataset_location", "")
            n_source = len(p.get("source_data_files", []))
            repos_str = ", ".join(
                f"{r['repo_type']}({r['inventory'].get('file_count', 0)} files)"
                for r in p["repositories"] if r.get("inventory", {}).get("success")
            )
            detail = repos_str or f"{n_source} source files" if n_source else gpt_loc
            logger.info(
                f"  [{p['priority_score']:5.1f}] [{status:>17}] {p['title'][:50]}"
            )
            logger.info(
                f"         {p['journal']} | {detail}"
            )

    # Show upon_request papers
    upon_req = [p for p in papers if p["dataset_status"] == "upon_request"]
    if upon_req:
        logger.info("-" * 60)
        logger.info(f"PAPERS WITH DATA UPON REQUEST: {len(upon_req)}")
        for p in upon_req[:5]:
            logger.info(f"  [{p['priority_score']:5.1f}] {p['title'][:60]}")

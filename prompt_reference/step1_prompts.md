# Step 1 Prompt Reference

Step 1 discovers candidate papers and scores them for downstream dataset work.
It uses deterministic query construction plus an optional GPT screening prompt.

## Active Role

Step 1 does **not** download datasets or inspect files. It only produces a high-recall candidate list with metadata, dataset-signal hints, and a `keep` / `maybe` / `drop` screening decision.

## Inputs

- Query configuration: `step1/config/step1_config*.yaml`
- Metadata APIs: Semantic Scholar, OpenAlex, CrossRef, arXiv
- Paper metadata: title, journal, year, abstract, DOI, URL

## Outputs

- `step1/output/step1_candidates_<timestamp>.json`
- `step1/output/step1_candidates_latest.json`
- `step1/output/step1_keep_maybe_<timestamp>.json`
- `step1/output/step1_run.log`

## GPT Use

Step 1 has two GPT prompt templates in `step1/gpt_client.py`:

1. Query generation prompt: available in code, but the current config notes that query LLM generation has been removed from the active query flow. Search queries are built from static topic / experiment / data keywords by `step1/query_generator.py`.
2. Paper screening prompt: active when `gpt.enabled=true`. This screens each candidate paper for field relevance, experimental character, soft-material mismatch, review status, and dataset mention.

## Prompt A: Query Generation

### System Prompt

```text
You are an expert in condensed matter physics and materials science research.
Your task is to generate effective search queries for academic paper APIs.
You understand what makes a good search query for finding experimental papers with open datasets.
```

### User Prompt Template

```text
Generate search queries to find condensed matter / materials science EXPERIMENTAL papers 
that provide open-access datasets (e.g., on Zenodo, Figshare, or as supplementary data).

Requirements:
- Papers should be from the last 5 years (2021-2026)
- Focus on hard condensed matter (NOT soft matter like polymers, gels, biomaterials)
- Papers should describe original experimental measurements (not purely computational/theoretical)
- Prioritize papers that explicitly mention datasets, source data, or data repositories

Generate queries for these APIs:
1. OpenAlex: general academic search, supports free text queries (3-8 words each)
2. CrossRef: DOI-centric search, works best with short queries (3-6 words each)
3. arXiv: preprint server, will be filtered to cond-mat category, so focus on specific topics + experimental keywords (2-4 words each)

Topics to cover (but not limited to):
- Moire / twisted bilayer systems
- Topological materials (insulators, semimetals, Weyl)
- 2D materials and van der Waals heterostructures
- Superconductivity
- Magnetic ordering, multiferroics, ferroelectrics
- Charge density waves, kagome metals
- Quantum oscillations, transport measurements
- Spectroscopy (ARPES, Raman, STM, neutron scattering)
- Thin films, epitaxial growth

Return JSON:
{
  "openalex": ["query1", "query2", ...],
  "crossref": ["query1", "query2", ...],
  "arxiv": ["query1", "query2", ...]
}
```

## Prompt B: Paper Screening

### System Prompt

```text
You are an expert in condensed matter physics and materials science.
Your task is to screen research papers for relevance.
You must return structured JSON judgments. Be accurate and concise.
```

### User Prompt Template

```text
Analyze this paper and answer each question.

Title: {title}
Journal: {journal}
Year: {year}
Abstract: {abstract}

Return JSON with these fields:
{
  "summary": "2 concise sentences describing what the paper did: material/system, method, and main finding",
  "candidate_rationale": "1 sentence explaining why this is or is not a useful UC LEAP candidate",
  "field_match": {
    "level": "strong" | "general" | "weak" | "none",
    "reason": "brief reason"
  },
  "experimental": {
    "level": "clear" | "likely" | "mixed" | "theory_only" | "uncertain",
    "reason": "brief reason"
  },
  "soft_material": {
    "flag": true | false,
    "reason": "brief reason"
  },
  "is_review": {
    "flag": true | false,
    "reason": "brief reason"
  },
  "dataset_mentioned": {
    "flag": true | false,
    "detail": "what dataset/data availability was mentioned, or 'none'"
  }
}

Definitions:
- field_match "strong": clearly condensed matter / materials science (topological, moire, superconductor, 2D materials, etc.)
- field_match "general": materials science related but not core condensed matter
- field_match "weak": tangentially related
- field_match "none": unrelated field
- experimental "clear": describes original experimental measurements
- experimental "likely": mentions experiments but not the main focus
- experimental "mixed": both experimental and computational
- experimental "theory_only": purely theoretical/computational
- soft_material: polymers, gels, biomaterials, colloids, liquid crystals, etc.
- is_review: review articles, perspectives, roadmaps
```

## Decision Logic

The GPT screening result is converted into scoring fields by `step1/scorer.py`.
Step 1 keeps recall high: uncertain papers can survive as `maybe` so Step 2 can check real dataset evidence.

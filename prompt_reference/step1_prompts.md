# Step 1 Prompts

This file summarizes the GPT prompt used in Step 1 candidate screening.
The prompt is applied after paper metadata and abstracts have already been collected from academic APIs.
Its role is to judge whether a paper is actually in the target field, whether it is experimental rather than purely theoretical, and whether it mentions any sign of available data.
The output is a structured JSON judgment that later feeds the Step 1 scoring and `keep / maybe / drop` decision.

## Prompt: Paper Screening

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
  "summary": "1-sentence summary of the research",
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

"""
Step 1 - Query Generator
=========================
Generates diverse search queries by combining topic, experiment, and data keywords.
Goal: maximize recall by creating a broad set of queries.
"""

import itertools
import random
from typing import List, Dict, Any


# Hand-crafted high-value queries that are known to find good candidates
MANUAL_QUERIES = [
    "condensed matter experimental source data Nature",
    "materials science transport measurements data availability",
    "moire 2D materials experimental dataset",
    "Raman materials experimental source data",
    "topological materials transport dataset",
    "twisted bilayer graphene experimental data repository",
    "quantum oscillations experimental source data",
    "superconductivity experimental measurements dataset",
    "van der Waals heterostructure transport data availability",
    "ARPES experimental data repository materials",
    "STM topological surface states source data",
    "magnetoresistance thin film experimental dataset",
    "2D materials spectroscopy open data",
    "correlated electron experimental data zenodo",
    "ferroelectric thin film measurement data figshare",
    "neutron scattering magnetic materials dataset",
    "X-ray diffraction thin film source data",
    "Hall effect quantum materials experimental data",
]


def generate_queries(config: Dict[str, Any]) -> List[str]:
    """
    Generate a diverse set of search queries from config keywords.

    Strategy:
    1. Use hand-crafted manual queries (known good patterns)
    2. Generate cross-product combinations: topic x experiment x data keyword
    3. Generate topic + data keyword pairs (simpler, broader)
    4. Deduplicate and shuffle

    Returns list of query strings.
    """
    queries = set()

    topic_kw = config.get("topic_keywords", [])
    experiment_kw = config.get("experiment_keywords", [])
    data_kw = config.get("data_keywords", [])

    # 1. Manual queries
    for q in MANUAL_QUERIES:
        queries.add(q)

    # 2. Cross-product: topic x experiment x data (sample to avoid explosion)
    cross_combos = list(itertools.product(topic_kw, experiment_kw, data_kw))
    if len(cross_combos) > 40:
        cross_combos = random.sample(cross_combos, 40)
    for t, e, d in cross_combos:
        queries.add(f"{t} {e} {d}")

    # 3. Topic x data (broader, good for recall)
    topic_data_combos = list(itertools.product(topic_kw, data_kw))
    if len(topic_data_combos) > 25:
        topic_data_combos = random.sample(topic_data_combos, 25)
    for t, d in topic_data_combos:
        queries.add(f"{t} {d}")

    # 4. Topic x experiment (for experimental match)
    topic_exp_combos = list(itertools.product(topic_kw, experiment_kw))
    if len(topic_exp_combos) > 20:
        topic_exp_combos = random.sample(topic_exp_combos, 20)
    for t, e in topic_exp_combos:
        queries.add(f"{t} {e}")

    query_list = sorted(queries)
    return query_list


def generate_api_specific_queries(config: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Generate queries tailored for each API's search syntax.

    Returns dict mapping API name -> list of queries.
    """
    base_queries = generate_queries(config)

    # Semantic Scholar: free text queries work well
    semantic_scholar_queries = base_queries.copy()

    # OpenAlex: supports concept-based search, but text search also works
    # We add some concept-focused queries
    openalex_queries = base_queries.copy()
    openalex_extra = [
        "condensed matter physics experimental dataset",
        "materials characterization source data",
        "quantum materials measurement open data",
        "thin film growth characterization data repository",
        "2D materials device measurement dataset",
    ]
    openalex_queries.extend(openalex_extra)

    # arXiv: cond-mat category filter already ensures field match.
    # Don't use data keywords (arXiv metadata search can't find them).
    # Focus on topic + experimental/measurement keywords for recall.
    arxiv_queries = []
    arxiv_topic_kw = [
        # Topological & quantum phases
        "topological insulator", "topological superconductor",
        "Weyl semimetal", "Dirac semimetal", "Majorana", "skyrmion",
        "Mott insulator", "heavy fermion", "Kondo", "spin liquid",
        "frustrated magnet", "vortex", "Josephson junction",
        # Superconductors
        "cuprate", "nickelate", "iron-based superconductor",
        # 2D / van der Waals
        "graphene", "TMD", "moiré", "twisted bilayer",
        "heterostructure", "van der Waals", "2D material",
        # Ordering & transitions
        "charge density wave", "phase transition", "exchange bias",
        # Functional materials
        "ferroelectric", "multiferroic", "thermoelectric", "piezoelectric",
        # Observables
        "quantum oscillation", "Fermi surface", "superconducting gap",
    ]
    arxiv_exp_kw = [
        "experimental", "measurement", "transport", "spectroscopy",
        "STM", "ARPES", "Raman", "neutron scattering", "XRD",
        "magnetoresistance", "Hall effect", "specific heat",
        "thin film", "single crystal",
    ]
    for t in arxiv_topic_kw:
        for e in arxiv_exp_kw:
            arxiv_queries.append(f"{t} {e}")
    # Also add standalone topic queries (arXiv cond-mat filter is enough)
    for t in arxiv_topic_kw:
        arxiv_queries.append(t)

    # CrossRef: good for DOI/metadata search, text queries
    crossref_queries = [q for q in base_queries if len(q.split()) <= 6]
    if len(crossref_queries) < 15:
        crossref_queries = base_queries[:30]

    # Europe PMC: supports full-text search, good for finding data availability mentions
    europe_pmc_queries = base_queries.copy()
    europe_pmc_extra = [
        "condensed matter experimental data availability",
        "2D materials source data supplementary",
        "topological materials measurement dataset",
        "thin film characterization open data",
        "quantum materials transport data repository",
    ]
    europe_pmc_queries.extend(europe_pmc_extra)

    return {
        "semantic_scholar": semantic_scholar_queries,
        "openalex": openalex_queries,
        "arxiv": arxiv_queries,
        "crossref": crossref_queries,
        "europe_pmc": europe_pmc_queries,
    }

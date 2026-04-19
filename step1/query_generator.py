"""
Step 1 - Query Generator
=========================
Generates diverse search queries by combining topic, experiment, and data keywords.
Goal: maximize recall by creating a broad set of queries.
"""

import itertools
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


TOPIC_FAMILIES = {
    "topological_quantum": [
        "topological insulator", "topological superconductor", "Weyl semimetal",
        "Dirac semimetal", "Majorana", "skyrmion", "spin-orbit coupling",
        "vortex", "Josephson junction", "Mott insulator", "heavy fermion",
        "Kondo", "spin liquid", "frustrated magnet",
    ],
    "superconductors": [
        "cuprate", "nickelate", "iron-based superconductor",
        "superconducting gap", "superconductivity",
    ],
    "two_d_vdw": [
        "graphene", "TMD", "moiré", "moire", "twisted bilayer",
        "heterostructure", "van der Waals", "2D material",
    ],
    "ordering_magnetism": [
        "charge density wave", "phase transition", "magnetic anisotropy",
        "exchange bias", "magnetism", "kagome",
    ],
    "functional_materials": [
        "ferroelectric", "multiferroic", "thermoelectric", "piezoelectric",
    ],
    "observables": [
        "Fermi surface", "band structure", "lattice constant",
        "quantum oscillation",
    ],
}


EXPERIMENT_FAMILIES = {
    "spectroscopy_microscopy": [
        "STM", "STS", "ARPES", "SET", "EELS", "Raman",
        "tunneling spectroscopy", "point-contact spectroscopy",
        "neutron scattering",
    ],
    "diffraction_imaging": ["XRD", "TEM", "AFM"],
    "growth_fabrication": [
        "MBE", "PLD", "CVD", "sputtering", "exfoliation",
        "flux growth", "Bridgman",
    ],
    "sample_forms": ["thin film", "single crystal", "bulk crystal"],
    "transport_thermo": [
        "magnetoresistance", "Hall effect", "specific heat",
        "de Haas-van Alphen", "Shubnikov-de Haas",
        "electronic transport", "thermal transport", "thermal coefficient",
        "transport measurements", "transport",
    ],
}


TOPIC_FAMILY_ORDER = list(TOPIC_FAMILIES)
EXPERIMENT_FAMILY_ORDER = list(EXPERIMENT_FAMILIES)


def generate_queries(config: Dict[str, Any]) -> List[str]:
    """
    Generate a diverse set of search queries from config keywords.

    Strategy:
    1. Use hand-crafted manual queries (known good patterns)
    2. Generate balanced topic x experiment x data keyword combinations
    3. Generate topic + data keyword pairs (simpler, broader)
    4. Generate topic + experiment pairs
    5. Deduplicate while preserving deterministic balanced order

    Returns list of query strings.
    """
    topic_kw = config.get("topic_keywords", [])
    experiment_kw = config.get("experiment_keywords", [])
    data_kw = config.get("data_keywords", [])

    cross_records = [
        record
        for t, e, d in itertools.product(topic_kw, experiment_kw, data_kw)
        for record in [_record(
            text=f"{t} {e} {d}",
            source="topic_exp_data",
            topic=t,
            experiment=e,
            data_keyword=d,
        )]
        if _is_compatible(record)
    ]
    topic_data_records = [
        _record(
            text=f"{t} {d}",
            source="topic_data",
            topic=t,
            data_keyword=d,
        )
        for t, d in itertools.product(topic_kw, data_kw)
    ]
    topic_exp_records = [
        record
        for t, e in itertools.product(topic_kw, experiment_kw)
        for record in [_record(
            text=f"{t} {e}",
            source="topic_exp",
            topic=t,
            experiment=e,
        )]
        if _is_compatible(record)
    ]

    queries = []
    queries.extend(MANUAL_QUERIES)
    queries.extend(_texts(_select_balanced_records(cross_records, limit=40)))
    queries.extend(_texts(_select_balanced_records(topic_data_records, limit=25)))
    queries.extend(_texts(_select_balanced_records(topic_exp_records, limit=20)))
    return _dedupe_preserve_order(queries)


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
    arxiv_queries = _build_arxiv_queries(arxiv_topic_kw, arxiv_exp_kw)

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


def _record(
    text: str,
    source: str,
    topic: str = "",
    experiment: str = "",
    data_keyword: str = "",
) -> Dict[str, str]:
    return {
        "text": text,
        "source": source,
        "topic": topic,
        "topic_family": _family_for_term(topic, TOPIC_FAMILIES, "other_topic"),
        "experiment": experiment,
        "experiment_family": _family_for_term(
            experiment, EXPERIMENT_FAMILIES, "other_experiment"
        ),
        "data_keyword": data_keyword,
    }


def _family_for_term(
    term: str,
    family_map: Dict[str, List[str]],
    default: str,
) -> str:
    term_norm = _norm(term)
    if not term_norm:
        return default
    for family, terms in family_map.items():
        for candidate in terms:
            cand_norm = _norm(candidate)
            if cand_norm and (cand_norm == term_norm or cand_norm in term_norm):
                return family
    return default


def _select_balanced_records(
    records: List[Dict[str, str]],
    limit: int,
) -> List[Dict[str, str]]:
    if limit <= 0:
        return []

    buckets: Dict[str, List[Dict[str, str]]] = {}
    for record in records:
        family = record.get("topic_family") or "other_topic"
        buckets.setdefault(family, []).append(record)

    family_order = [
        f for f in TOPIC_FAMILY_ORDER + sorted(buckets)
        if f in buckets
    ]
    for family in family_order:
        family_offset = _family_index(family, TOPIC_FAMILY_ORDER)
        buckets[family] = _interleave_by_experiment_family(
            buckets[family],
            offset=family_offset,
        )

    selected: List[Dict[str, str]] = []
    seen = set()
    while len(selected) < limit:
        added = False
        for family in family_order:
            queue = buckets.get(family, [])
            while queue:
                record = queue.pop(0)
                text_key = _norm(record.get("text", ""))
                if text_key in seen:
                    continue
                selected.append(record)
                seen.add(text_key)
                added = True
                break
            if len(selected) >= limit:
                break
        if not added:
            break
    return selected


def _is_compatible(record: Dict[str, str]) -> bool:
    topic_family = record.get("topic_family", "")
    exp_family = record.get("experiment_family", "")
    topic = _norm(record.get("topic", ""))
    experiment = _norm(record.get("experiment", ""))

    if not experiment:
        return True

    if topic_family == "two_d_vdw":
        if experiment in {"bridgman", "flux growth", "bulk crystal", "single crystal"}:
            return False
        if exp_family == "growth_fabrication":
            return experiment in {"mbe", "cvd", "exfoliation", "pld"}
        return True

    if topic_family == "observables":
        if exp_family in {"growth_fabrication", "sample_forms"}:
            return False
        return True

    if topic_family == "functional_materials":
        if exp_family == "transport_thermo":
            return (
                "thermoelectric" in topic
                and experiment in {"thermal transport", "thermal coefficient"}
            )
        if exp_family == "growth_fabrication":
            return experiment in {"mbe", "pld", "cvd", "sputtering"}
        return True

    if topic_family == "superconductors":
        if exp_family == "growth_fabrication":
            return experiment in {"flux growth", "bridgman", "mbe", "pld"}
        return True

    if topic_family == "topological_quantum":
        if exp_family == "growth_fabrication":
            return experiment in {"flux growth", "bridgman", "mbe", "pld", "exfoliation"}
        return True

    if topic_family == "ordering_magnetism":
        if exp_family == "growth_fabrication":
            return experiment in {"flux growth", "bridgman", "mbe", "pld", "sputtering"}
        return True

    return True


def _build_arxiv_queries(topics: List[str], experiments: List[str]) -> List[str]:
    topic_records = [
        _record(text=topic, source="arxiv_topic", topic=topic)
        for topic in topics
    ]
    topic_order = _texts(_select_balanced_records(topic_records, limit=len(topic_records)))
    experiment_order = _balanced_experiment_order(experiments)

    queries = []
    if topic_order and experiment_order:
        total_pairs = len(topic_order) * len(experiment_order)
        for idx in range(total_pairs):
            topic = topic_order[idx % len(topic_order)]
            experiment = experiment_order[idx % len(experiment_order)]
            record = _record(
                text=f"{topic} {experiment}",
                source="arxiv_topic_exp",
                topic=topic,
                experiment=experiment,
            )
            if _is_compatible(record):
                queries.append(record["text"])

    # Broad standalone topic queries are useful on arXiv because the cond-mat
    # category filter already constrains the scientific domain.
    queries.extend(topic_order)
    return _dedupe_preserve_order(queries)


def _balanced_experiment_order(experiments: List[str]) -> List[str]:
    records = [
        _record(text=experiment, source="experiment", experiment=experiment)
        for experiment in experiments
    ]
    buckets: Dict[str, List[str]] = {}
    for record in records:
        family = record.get("experiment_family") or "other_experiment"
        buckets.setdefault(family, []).append(record["text"])

    family_order = [
        family for family in EXPERIMENT_FAMILY_ORDER + sorted(buckets)
        if family in buckets
    ]
    for family in family_order:
        buckets[family] = sorted(buckets[family])

    result = []
    while True:
        added = False
        for family in family_order:
            queue = buckets.get(family, [])
            if queue:
                result.append(queue.pop(0))
                added = True
        if not added:
            break
    return result


def _family_index(value: str, order: List[str]) -> int:
    try:
        return order.index(value)
    except ValueError:
        return len(order)


def _interleave_by_experiment_family(
    records: List[Dict[str, str]],
    offset: int = 0,
) -> List[Dict[str, str]]:
    topic_buckets: Dict[str, List[Dict[str, str]]] = {}
    for record in records:
        topic = record.get("topic") or record.get("text", "")
        topic_buckets.setdefault(topic, []).append(record)

    topic_order = sorted(topic_buckets)
    exp_order = EXPERIMENT_FAMILY_ORDER + sorted(
        key
        for values in topic_buckets.values()
        for key in {v.get("experiment_family") or "other_experiment" for v in values}
        if key not in EXPERIMENT_FAMILY_ORDER
    )
    if exp_order:
        offset = offset % len(exp_order)
        exp_order = exp_order[offset:] + exp_order[:offset]

    for topic, values in topic_buckets.items():
        values_by_exp: Dict[str, List[Dict[str, str]]] = {}
        for record in values:
            exp_key = record.get("experiment_family") or "other_experiment"
            values_by_exp.setdefault(exp_key, []).append(record)

        interleaved_topic_values: List[Dict[str, str]] = []
        for exp_key in exp_order:
            values_by_exp[exp_key] = sorted(
                values_by_exp.get(exp_key, []),
                key=lambda r: (
                    r.get("data_keyword", ""),
                    r.get("experiment", ""),
                    r.get("text", ""),
                ),
            )

        while True:
            added = False
            for exp_key in exp_order:
                queue = values_by_exp.get(exp_key, [])
                if queue:
                    interleaved_topic_values.append(queue.pop(0))
                    added = True
            if not added:
                break
        topic_buckets[topic] = interleaved_topic_values

    result: List[Dict[str, str]] = []
    while True:
        added = False
        for topic in topic_order:
            queue = topic_buckets.get(topic, [])
            if queue:
                result.append(queue.pop(0))
                added = True
        if not added:
            break
    return result


def _texts(records: List[Dict[str, str]]) -> List[str]:
    return [record["text"] for record in records]


def _dedupe_preserve_order(queries: List[str]) -> List[str]:
    result = []
    seen = set()
    for query in queries:
        key = _norm(query)
        if key and key not in seen:
            result.append(query)
            seen.add(key)
    return result


def _norm(text: str) -> str:
    return " ".join((text or "").lower().replace("é", "e").split())

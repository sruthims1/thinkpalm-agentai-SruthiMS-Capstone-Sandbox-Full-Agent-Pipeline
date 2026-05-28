"""
Coverage calculator — maps generated Gherkin scenarios against extracted
requirements and identifies gaps, with special focus on safety-critical
and compliance-related uncovered areas.
"""

import re
from difflib import SequenceMatcher


# Keywords that flag a requirement as safety-critical or compliance-related
SAFETY_KEYWORDS = [
    "safety", "critical", "emergency", "block", "departure", "expired",
    "violation", "compliance", "mandatory", "authority", "notify", "alert",
    "restrict", "prevent", "minimum", "maximum", "deadline", "overdue",
]

COMPLIANCE_KEYWORDS = [
    "stcw", "mlc", "ism", "marpol", "solas", "isps", "fal", "regulation",
    "convention", "certificate", "compliance", "authorisation", "approval",
    "imdg", "eca", "colregs", "imo",
]

REGULATION_MAP = {
    "certificate": "STCW Convention",
    "expiry":      "STCW Convention",
    "rest hours":  "MLC 2006 Regulation 2.3",
    "fatigue":     "MLC 2006 Regulation 2.3",
    "watch":       "STCW Chapter VIII",
    "incident":    "ISM Code",
    "near miss":   "ISM Code",
    "port call":   "FAL Convention",
    "pre-arrival": "FAL Convention / ISPS Code",
    "customs":     "FAL Convention",
    "dangerous goods": "IMDG Code",
    "eca":         "MARPOL Annex VI",
    "sulphur":     "MARPOL Annex VI",
    "piracy":      "IMO MSC-FAL.1/Circ.3",
    "voyage":      "COLREGS 1972",
}


def calculate_coverage(
    requirements: list[str],
    scenarios:    list[str],
    feature_name: str = "",
) -> dict:
    """
    Map scenarios against requirements and produce a coverage report.

    Args:
        requirements: list of requirement strings extracted by Domain Analyst
        scenarios:    list of scenario titles from BDD Generator
        feature_name: name of the feature being analysed

    Returns:
        dict with coverage metrics, gaps, and critical gap analysis
    """
    if not requirements:
        return _empty_report(feature_name, reason="No requirements provided")
    if not scenarios:
        return _empty_report(feature_name, reason="No scenarios provided")

    covered        = []
    uncovered      = []
    partial        = []
    gap_details    = []
    critical_gaps  = []

    for req in requirements:
        match_score, best_scenario = _best_match(req, scenarios)

        if match_score >= 0.55:
            covered.append({
                "requirement": req,
                "covered_by":  best_scenario,
                "confidence":  round(match_score, 2),
            })
        elif match_score >= 0.30:
            partial.append({
                "requirement": req,
                "closest_scenario": best_scenario,
                "confidence": round(match_score, 2),
            })
            gap_details.append(f"Partially covered: {req}")
            if _is_safety_critical(req):
                critical_gaps.append(
                    f"[SAFETY] Partial coverage only: '{req}' — "
                    f"closest scenario: '{best_scenario}'"
                )
        else:
            uncovered.append(req)
            gap_details.append(f"Not covered: {req}")
            if _is_safety_critical(req):
                reg = _find_regulation(req)
                critical_gaps.append(
                    f"[SAFETY-CRITICAL] No test for: '{req}'"
                    + (f" — Regulation: {reg}" if reg else "")
                )

    total        = len(requirements)
    fully_covered = len(covered)
    pct          = round((fully_covered / total) * 100, 1) if total > 0 else 0.0

    # ── Edge case analysis ─────────────────────────────────────────────────────
    edge_case_gaps = _detect_missing_edge_cases(requirements, scenarios, feature_name)

    # ── Regulation traceability ────────────────────────────────────────────────
    reg_coverage = _build_regulation_coverage(requirements, covered)

    return {
        "feature_name":        feature_name,
        "total_requirements":  total,
        "covered_count":       fully_covered,
        "partial_count":       len(partial),
        "uncovered_count":     len(uncovered),
        "coverage_percentage": pct,
        "covered":             covered,
        "partial":             partial,
        "uncovered":           uncovered,
        "gaps":                gap_details,
        "critical_gaps":       critical_gaps,
        "edge_case_gaps":      edge_case_gaps,
        "regulation_coverage": reg_coverage,
        "summary": (
            f"{pct}% coverage ({fully_covered}/{total} requirements). "
            f"{len(critical_gaps)} safety-critical gap(s) identified."
        ),
    }


def _best_match(requirement: str, scenarios: list[str]) -> tuple[float, str]:
    """Find the scenario that best covers a requirement using fuzzy + keyword matching."""
    req_lower = requirement.lower()
    best_score = 0.0
    best_scenario = ""

    req_keywords = set(re.findall(r'\b\w{4,}\b', req_lower))

    for scenario in scenarios:
        sc_lower = scenario.lower()
        sc_keywords = set(re.findall(r'\b\w{4,}\b', sc_lower))

        # Sequence similarity
        seq_score = SequenceMatcher(None, req_lower, sc_lower).ratio()

        # Keyword overlap score
        overlap = req_keywords & sc_keywords
        kw_score = len(overlap) / max(len(req_keywords), 1)

        # Combined score — weight keywords more heavily
        combined = (seq_score * 0.35) + (kw_score * 0.65)

        if combined > best_score:
            best_score    = combined
            best_scenario = scenario

    return best_score, best_scenario


def _is_safety_critical(requirement: str) -> bool:
    req_lower = requirement.lower()
    return any(kw in req_lower for kw in SAFETY_KEYWORDS + COMPLIANCE_KEYWORDS)


def _find_regulation(requirement: str) -> str:
    req_lower = requirement.lower()
    for keyword, regulation in REGULATION_MAP.items():
        if keyword in req_lower:
            return regulation
    return ""


def _detect_missing_edge_cases(
    requirements: list[str],
    scenarios: list[str],
    feature_name: str,
) -> list[str]:
    """Detect common maritime edge cases that are likely missing from the scenario set."""
    gaps = []
    scenarios_lower = " ".join(s.lower() for s in scenarios)
    feature_lower   = feature_name.lower()

    edge_case_checks = [
        # Date boundary cases
        ("expir" in " ".join(r.lower() for r in requirements),
         "boundary" not in scenarios_lower and "exactly" not in scenarios_lower,
         "Missing boundary test: certificate/deadline expiry on exact boundary date (T±0 days)"),

        # Midnight/date-span cases
        ("rest" in " ".join(r.lower() for r in requirements) or "fatigue" in feature_lower,
         "midnight" not in scenarios_lower and "span" not in scenarios_lower,
         "Missing edge case: rest period spanning midnight boundary"),

        # Zero/empty value cases
        (True,
         "zero" not in scenarios_lower and "empty" not in scenarios_lower and "blank" not in scenarios_lower,
         "Missing validation test: zero or empty field submission"),

        # Concurrent/multiple record cases
        ("violation" in " ".join(r.lower() for r in requirements) or "expired" in " ".join(r.lower() for r in requirements),
         "multiple" not in scenarios_lower,
         "Missing edge case: multiple simultaneous violations or expired records"),

        # Role-based access
        ("approval" in " ".join(r.lower() for r in requirements) or "authoris" in " ".join(r.lower() for r in requirements),
         "unauthor" not in scenarios_lower and "permission" not in scenarios_lower,
         "Missing security test: unauthorised role attempting restricted action"),

        # Override/emergency case
        ("block" in " ".join(r.lower() for r in requirements) or "restrict" in " ".join(r.lower() for r in requirements),
         "override" not in scenarios_lower and "emergency" not in scenarios_lower,
         "Missing edge case: emergency override of a blocked action"),
    ]

    for condition, missing, message in edge_case_checks:
        if condition and missing:
            gaps.append(message)

    return gaps


def _build_regulation_coverage(requirements: list[str], covered: list[dict]) -> list[dict]:
    """Build a traceability table of regulations vs covered/uncovered requirements."""
    reg_map: dict[str, dict] = {}

    for req in requirements:
        reg = _find_regulation(req)
        if not reg:
            reg = "General / Operational"
        if reg not in reg_map:
            reg_map[reg] = {"regulation": reg, "total": 0, "covered": 0}
        reg_map[reg]["total"] += 1

    covered_reqs = {c["requirement"] for c in covered}
    for req in requirements:
        reg = _find_regulation(req) or "General / Operational"
        if req in covered_reqs:
            reg_map[reg]["covered"] += 1

    result = []
    for entry in reg_map.values():
        pct = round((entry["covered"] / entry["total"]) * 100, 1) if entry["total"] > 0 else 0
        result.append({**entry, "coverage_pct": pct})

    return sorted(result, key=lambda x: x["coverage_pct"])


def _empty_report(feature_name: str, reason: str) -> dict:
    return {
        "feature_name":        feature_name,
        "total_requirements":  0,
        "covered_count":       0,
        "partial_count":       0,
        "uncovered_count":     0,
        "coverage_percentage": 0.0,
        "covered":             [],
        "partial":             [],
        "uncovered":           [],
        "gaps":                [reason],
        "critical_gaps":       [],
        "edge_case_gaps":      [],
        "regulation_coverage": [],
        "summary":             f"Coverage could not be calculated: {reason}",
    }

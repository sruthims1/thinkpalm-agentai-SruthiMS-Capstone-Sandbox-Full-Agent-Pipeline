"""
Agent 4 — QAAuditorAgent
Produces a requirements traceability matrix, identifies coverage gaps
(especially P1 safety-critical), and scores the overall test quality.
This is the final stage of the MaritimeTestAI pipeline.
"""

from __future__ import annotations
import json, logging, concurrent.futures
from typing import Callable

from services.llm_service import llm
from tools.tool_registry import dispatch
from memory.short_term import session_memory

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a senior maritime QA auditor (ISM Code, IMO MSC standards, PSC inspection authority).
Review the generated test scenarios against requirements and produce an audit report.

Return ONLY this JSON — no prose:
{
  "traceability_matrix": [
    {
      "req_id": "R1",
      "requirement": "description",
      "scenario": "matching scenario title or null",
      "status": "covered|partial|gap",
      "regulation": "STCW|MLC|ISM|SOLAS|MARPOL|FAL"
    }
  ],
  "coverage_gaps": [
    {
      "gap": "description of missing coverage",
      "priority": "P1|P2|P3",
      "regulation": "regulation reference",
      "recommendation": "Add scenario: ..."
    }
  ],
  "overall_score": 0-100,
  "p1_coverage_pct": 0-100,
  "p2_coverage_pct": 0-100,
  "executive_summary": "2-sentence summary",
  "recommendations": ["..."]
}

Scoring: start at 100, deduct 10 per uncovered P1 requirement, 3 per uncovered P2.
Any P1 gap = critical risk that must be flagged in recommendations."""


class QAAuditorAgent:
    """Agent 4 — Traceability matrix, coverage gap analysis, and audit scoring."""

    name = "QA Auditor"

    def __init__(self, log_callback: Callable[[str], None] | None = None) -> None:
        self._log = log_callback or log.info

    def audit(
        self,
        feature_name: str,
        feature_description: str,
        domain_analysis: dict,
        gherkin_result: dict,
        playwright_result: dict,
    ) -> dict:
        self._log(f"[{self.name}] Auditing: {feature_name}")
        # Enrich from short-term memory if LangGraph state is sparse
        if not domain_analysis:
            domain_analysis = session_memory.get("domain_analysis") or {}
        if not gherkin_result:
            gherkin_result = session_memory.get("gherkin_output") or {}
        if not playwright_result:
            playwright_result = session_memory.get("playwright_scripts") or {}

        p1_reqs   = domain_analysis.get("p1_safety_requirements", [])
        p2_reqs   = domain_analysis.get("p2_compliance_requirements", [])
        p3_reqs   = domain_analysis.get("p3_operational_requirements", [])
        scenarios = gherkin_result.get("scenario_titles", [])
        coverage  = (playwright_result.get("coverage_report", {}) or playwright_result.get("risk_report", {}))

        sc_list  = "\n".join(f"  - {s}" for s in scenarios[:20])
        req_list = (
            "\n".join(f"  [P1] {r}" for r in p1_reqs[:6]) + "\n" +
            "\n".join(f"  [P2] {r}" for r in p2_reqs[:5]) + "\n" +
            "\n".join(f"  [P3] {r}" for r in p3_reqs[:4])
        ).strip()

        user_msg = f"""Audit test coverage for: {feature_name}

REQUIREMENTS ({len(p1_reqs)} P1-safety + {len(p2_reqs)} P2-compliance + {len(p3_reqs)} P3-operational):
{req_list}

GENERATED SCENARIOS ({len(scenarios)} total):
{sc_list}

Regulations: {', '.join(domain_analysis.get('applicable_regulations', [])[:5])}
PSC Detention Triggers: {'; '.join(domain_analysis.get('psc_detention_triggers', [])[:3])}
Current Test Coverage: {(coverage or {}).get('coverage_percentage', 0)}%

Map each requirement to a scenario (or mark as gap).
Flag all P1 gaps as critical risk."""

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(llm.complete_gen, SYSTEM_PROMPT, user_msg, 1800)
                raw    = future.result(timeout=45)
            result = self._parse_json(raw)
        except concurrent.futures.TimeoutError:
            self._log(f"[{self.name}] LLM timed out (45s) — computing audit from coverage data")
            result = self._fallback_audit(feature_name, p1_reqs, p2_reqs, p3_reqs, scenarios, coverage or {})
        except Exception as exc:
            self._log(f"[{self.name}] LLM failed ({exc}) — computing audit from coverage data")
            result = self._fallback_audit(feature_name, p1_reqs, p2_reqs, p3_reqs, scenarios, coverage or {})

        result.setdefault("feature_name", feature_name)
        result.setdefault("playwright_coverage_pct", (coverage or {}).get("coverage_percentage", 0))

        safe_name = feature_name.lower().replace(" ", "_")
        dispatch("write_test_file", {
            "filename":  f"{safe_name}_audit_report",
            "content":   json.dumps(result, indent=2),
            "file_type": "report",
        })

        self._log(
            f"[{self.name}] Complete — score: {result.get('overall_score', 0)}/100, "
            f"gaps: {len(result.get('coverage_gaps', []))}, "
            f"P1 coverage: {result.get('p1_coverage_pct', 0)}%"
        )
        return result

    @staticmethod
    def _parse_json(raw: str) -> dict:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise ValueError("No JSON block found")

    @staticmethod
    def _fallback_audit(
        feature_name: str,
        p1_reqs: list, p2_reqs: list, p3_reqs: list,
        scenarios: list, coverage: dict,
    ) -> dict:
        """Compute audit report from coverage data when LLM is unavailable."""
        matrix: list[dict] = []

        def _find_scenario(req: str) -> str | None:
            words = req.lower().split()[:4]
            return next((s for s in scenarios if sum(1 for w in words if w in s.lower()) >= 2), None)

        for i, r in enumerate(p1_reqs):
            sc = _find_scenario(r)
            matrix.append({"req_id": f"R{i+1}", "requirement": r, "scenario": sc, "status": "covered" if sc else "gap", "regulation": "P1-SAFETY"})
        for i, r in enumerate(p2_reqs):
            sc = _find_scenario(r)
            matrix.append({"req_id": f"C{i+1}", "requirement": r, "scenario": sc, "status": "covered" if sc else "partial", "regulation": "P2-COMPLIANCE"})
        for i, r in enumerate(p3_reqs[:4]):
            sc = _find_scenario(r)
            matrix.append({"req_id": f"O{i+1}", "requirement": r, "scenario": sc, "status": "covered" if sc else "gap", "regulation": "P3-OPERATIONAL"})

        p1_covered  = sum(1 for m in matrix if m["regulation"] == "P1-SAFETY"     and m["status"] == "covered")
        p2_covered  = sum(1 for m in matrix if m["regulation"] == "P2-COMPLIANCE" and m["status"] == "covered")
        p1_total    = max(len(p1_reqs), 1)
        p2_total    = max(len(p2_reqs), 1)
        p1_pct      = round(p1_covered / p1_total * 100)
        p2_pct      = round(p2_covered / p2_total * 100)
        score       = max(0, 100 - (p1_total - p1_covered) * 10 - (p2_total - p2_covered) * 3)

        gaps = [
            {"gap": m["requirement"], "priority": "P1", "regulation": "Safety-Critical",
             "recommendation": f"Add scenario covering: {m['requirement']}"}
            for m in matrix if m["regulation"] == "P1-SAFETY" and m["status"] == "gap"
        ] + [
            {"gap": m["requirement"], "priority": "P2", "regulation": "Compliance",
             "recommendation": f"Add compliance test for: {m['requirement']}"}
            for m in matrix if m["regulation"] == "P2-COMPLIANCE" and m["status"] in ("gap", "partial")
        ]

        recs: list[str] = []
        if p1_pct < 100:
            recs.append(f"CRITICAL: P1 safety coverage is {p1_pct}% — all P1 requirements must have dedicated test scenarios before vessel release")
        if p2_pct < 80:
            recs.append(f"P2 compliance coverage is {p2_pct}% — review regulatory gaps before PSC inspection")
        if len(scenarios) < 10:
            recs.append("Consider increasing scenario count — at least 10 scenarios recommended for safety-critical features")
        recs.append("Schedule automated Playwright test execution against the staging environment before each port call")
        if not recs:
            recs.append("All P1 safety requirements covered. Schedule regression test run before next departure.")

        return {
            "traceability_matrix": matrix,
            "coverage_gaps":       gaps[:10],
            "overall_score":       score,
            "p1_coverage_pct":     p1_pct,
            "p2_coverage_pct":     p2_pct,
            "executive_summary":   (
                f"Feature '{feature_name}' audit: P1 Safety {p1_pct}%, P2 Compliance {p2_pct}%, "
                f"Overall Score {score}/100. "
                f"{len([g for g in gaps if g['priority']=='P1'])} critical P1 gaps identified."
            ),
            "recommendations": recs,
        }

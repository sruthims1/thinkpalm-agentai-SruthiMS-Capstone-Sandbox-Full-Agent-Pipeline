"""
Agent 1 — MaritimeDomainAgent
Analyzes a maritime software feature for IMO/SOLAS/STCW/MLC/MARPOL/ISM risks,
returning enriched safety requirements, boundary values, and PSC detention triggers.
"""

from __future__ import annotations
import json, logging, concurrent.futures
from typing import Callable

from services.llm_service import llm
from memory.short_term import session_memory

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a maritime safety domain expert (IMO/SOLAS/STCW/MLC/MARPOL/ISM/ISPS).
Analyze a maritime software feature and return a structured risk assessment as JSON.

Return ONLY this JSON — no prose, no markdown:
{
  "risk_level": "HIGH|MEDIUM|LOW",
  "applicable_regulations": ["STCW A-VIII/1", "MLC 2006 Reg 2.3", ...],
  "p1_safety_requirements": ["...", ...],
  "p2_compliance_requirements": ["...", ...],
  "p3_operational_requirements": ["...", ...],
  "boundary_values": ["min 10h rest per 24h", "max 14h work per 24h", "30-day renewal window", ...],
  "psc_detention_triggers": ["expired certificate at departure", "fatigue hours below threshold", ...],
  "mandatory_edge_cases": ["boundary exactly at threshold", "1 day past expiry", "role without permission", ...]
}

Use EXACT thresholds from the KB context provided. Focus on crew safety, vessel seaworthiness, and PSC detention risk."""


class MaritimeDomainAgent:
    """Agent 1 — Maritime risk analysis and domain enrichment."""

    name = "Maritime Domain Expert"

    def __init__(self, log_callback: Callable[[str], None] | None = None) -> None:
        self._log    = log_callback or log.info
        self._kb     = self._load_kb()
        self._ltm    = self._load_ltm()
        self._app_kb = self._load_app_kb()

    @staticmethod
    def _load_kb():
        try:
            from memory.maritime_kb import MaritimeKnowledgeBase
            return MaritimeKnowledgeBase()
        except Exception as exc:
            log.warning(f"KB unavailable: {exc}")
            return None

    @staticmethod
    def _load_ltm():
        try:
            from memory.long_term import LongTermMemory
            return LongTermMemory()
        except Exception as exc:
            log.warning(f"LTM unavailable: {exc}")
            return None

    @staticmethod
    def _load_app_kb():
        try:
            from memory.app_features_kb import AppFeaturesKB
            return AppFeaturesKB()
        except Exception as exc:
            log.warning(f"App KB unavailable: {exc}")
            return None

    def _query_kb(self, feature_name: str, feature_description: str) -> str:
        if not self._kb:
            return ""
        try:
            query   = f"{feature_name} {feature_description[:200]}"
            results = self._kb.query(query, n_results=4)
            if not results:
                return ""
            lines = ["=== Authoritative KB — use these EXACT thresholds ==="]
            for r in results:
                lines.append(f"[{r['regulation']} — {r['clause']}]")
                lines.append(r["text"][:350])
                impls = r.get("implications", [])[:4]
                if impls:
                    lines.append("Test implications: " + " | ".join(impls))
                lines.append("")
            return "\n".join(lines)
        except Exception as exc:
            log.warning(f"KB query failed: {exc}")
            return ""

    def analyze(self, feature_name: str, feature_description: str) -> dict:
        self._log(f"[{self.name}] Analyzing: {feature_name}")

        kb_context  = self._query_kb(feature_name, feature_description)
        ltm_context = self._query_ltm(feature_name, feature_description)
        app_context = self._query_app_kb(feature_name)

        if kb_context:
            self._log(f"[{self.name}] KB enrichment: {kb_context.count('[')} regulation(s) retrieved")
        if ltm_context:
            self._log(f"[{self.name}] LTM enrichment: prior analysis found for similar feature")
        if app_context:
            self._log(f"[{self.name}] App KB enrichment: mock app feature context loaded")

        user_msg = f"""Analyze this maritime software feature for safety and compliance risks:

Feature: {feature_name}

Description:
{feature_description[:1200]}

{kb_context}

{ltm_context}

{app_context}

Return a JSON risk assessment using the exact thresholds from the KB context above.
Ensure mandatory_edge_cases covers every workflow and testable state listed in the App Feature Context."""

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(llm.complete_gen, SYSTEM_PROMPT, user_msg, 1200)
                raw = future.result(timeout=45)
            result = self._parse_json(raw)
        except concurrent.futures.TimeoutError:
            self._log(f"[{self.name}] LLM timed out (45s) — using keyword fallback")
            result = self._keyword_fallback(feature_name, feature_description)
        except Exception as exc:
            self._log(f"[{self.name}] LLM failed ({exc}) — using keyword fallback")
            result = self._keyword_fallback(feature_name, feature_description)

        result.setdefault("feature_name", feature_name)
        self._log(
            f"[{self.name}] Complete — risk: {result.get('risk_level', '?')}, "
            f"regs: {len(result.get('applicable_regulations', []))}, "
            f"P1: {len(result.get('p1_safety_requirements', []))}"
        )
        session_memory.set("domain_analysis", result)
        return result

    def _query_app_kb(self, feature_name: str) -> str:
        """Return compact mock app feature context for the given feature."""
        if not self._app_kb:
            return ""
        try:
            result = self._app_kb.query(feature_name)
            if not result:
                return ""
            # Keep output token-efficient: pipe-separated, max 3 workflows + 4 states + 2 validations
            workflows = " | ".join(result["workflows"][:3])
            states    = " | ".join(result["testable_states"][:4])
            validations = " | ".join(result["validations"][:2])
            return (
                f"=== App Feature Context: {result['feature']} ({result['url']}) ===\n"
                f"Workflows: {workflows}\n"
                f"Testable states: {states}\n"
                f"Validations: {validations}"
            )
        except Exception as exc:
            log.warning(f"[{self.name}] App KB query failed: {exc}")
            return ""

    def _query_ltm(self, feature_name: str, feature_description: str) -> str:
        """Search long-term memory for prior analyses of similar features."""
        if not self._ltm:
            return ""
        try:
            if self._ltm.get_stats()["total_analyses"] == 0:
                return ""
            query  = f"{feature_name} {feature_description[:200]}"
            prior  = self._ltm.search_similar_analyses(query, n_results=2)
            if not prior:
                return ""
            lines = ["=== Long-Term Memory — Prior Analyses (use as supporting context only) ==="]
            for p in prior:
                meta = p.get("metadata", {})
                fn   = meta.get("feature_name", "")
                if fn.lower() == feature_name.lower():
                    continue
                sim = p.get("similarity", 0) or 0
                if sim < 0.5:
                    continue
                risk = meta.get("risk_level", "")
                analysis_json = meta.get("analysis_json", "{}")
                try:
                    import json as _j
                    pa   = _j.loads(analysis_json)
                    regs = pa.get("applicable_regulations", [])[:3]
                    p1s  = pa.get("p1_safety_requirements", [])[:2]
                    lines.append(f"[Prior: {fn} | Risk: {risk} | Similarity: {sim:.2f}]")
                    if regs:
                        lines.append(f"  Regulations: {', '.join(regs)}")
                    if p1s:
                        lines.append(f"  P1 requirements: {'; '.join(p1s)}")
                except Exception:
                    lines.append(f"[Prior: {fn} | Risk: {risk}]")
            return "\n".join(lines) if len(lines) > 1 else ""
        except Exception as exc:
            log.warning(f"[{self.name}] LTM query failed: {exc}")
            return ""

    # ── Helpers ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_json(raw: str) -> dict:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise ValueError("No JSON block found in LLM response")

    @staticmethod
    def _keyword_fallback(feature_name: str, description: str) -> dict:
        text = (feature_name + " " + description).lower()

        risk = (
            "HIGH"   if any(k in text for k in {"cert", "expir", "fatigue", "rest", "safety", "block", "depart", "solas"})
            else "MEDIUM"
        )
        regs: list[str] = []
        if any(k in text for k in {"cert", "stcw", "officer", "competency"}):
            regs.append("STCW 1978 (as amended)")
        if any(k in text for k in {"rest", "fatigue", "mlc", "working hours", "watch"}):
            regs += ["MLC 2006 Reg 2.3", "STCW A-VIII/1"]
        if any(k in text for k in {"voyage", "route", "navigation", "chart"}):
            regs.append("SOLAS Chapter V")
        if any(k in text for k in {"incident", "ism", "near-miss", "accident"}):
            regs.append("ISM Code (Res. A.741(18))")
        if any(k in text for k in {"port", "fal", "arrival", "pre-arrival"}):
            regs.append("FAL Convention 1965")
        if any(k in text for k in {"marpol", "fuel", "emission", "eca"}):
            regs.append("MARPOL Annex VI")

        return {
            "risk_level":                  risk,
            "applicable_regulations":      regs or ["SOLAS", "STCW 1978", "MLC 2006"],
            "p1_safety_requirements":      [
                f"All {feature_name} safety-critical thresholds must be enforced",
                f"Departure must be blocked when {feature_name.lower()} is non-compliant",
            ],
            "p2_compliance_requirements":  [
                f"{feature_name} records must satisfy regulatory audit requirements",
                "All regulatory deadlines must trigger automated alerts",
            ],
            "p3_operational_requirements": [
                f"Officers must be able to update {feature_name.lower()} records",
                "Dashboard must display current compliance status",
            ],
            "boundary_values":             [
                "Minimum 10 hours rest per 24-hour period",
                "Maximum 14 hours work per 24-hour period",
                "Minimum 77 hours rest per 7-day period",
                "30-day advance renewal warning",
            ],
            "psc_detention_triggers":      [
                f"Expired {feature_name.lower()} certificate at port departure",
                "Crew rest hours below MLC/STCW minimum threshold",
            ],
            "mandatory_edge_cases":        [
                "Boundary condition: record expires exactly at threshold date",
                "Negative: operation attempted with expired/invalid record",
                "Role boundary: unauthorized user attempts privileged action",
            ],
        }

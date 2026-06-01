"""
Agent 2 — TestStrategistAgent
Generates Gherkin BDD scenarios from domain-enriched requirements,
applying maritime-specific test patterns (Two-Deadline, Block-Override-Audit,
Role-Escalation).
"""

from __future__ import annotations
import logging, concurrent.futures
from typing import Callable

from services.llm_service import llm
from tools.gherkin_validator import validate_gherkin
from tools.tool_registry import dispatch, TOOL_SCHEMAS

# Schema sent to the LLM so it can call validate_gherkin itself
_VALIDATE_SCHEMA = next(t for t in TOOL_SCHEMAS if t["name"] == "validate_gherkin")

_TOOL_INSTRUCTIONS = (
    "\n\nTOOL USE (mandatory): After generating the Gherkin feature text, call the "
    "validate_gherkin tool with your full output. If the tool returns scenario_count < 6 "
    "or safety_tagged_count < 2, revise your Gherkin and call validate_gherkin again. "
    "Once validation passes, return the final Gherkin text in your response."
)

# Compact system prompt for the tool-calling path — intentionally short to stay
# under Groq's payload limit when feature descriptions are long (e.g. from JIRA).
# The full SYSTEM_PROMPT (with complete UI detail) is used in the fallback path.
_TOOL_SYSTEM_PROMPT = (
    "You are a BDD test analyst for a maritime web app at http://localhost:5000. "
    "Generate 8-12 Gherkin scenarios. P1 safety-critical first. Scenario Outline for boundaries. "
    "MANDATORY: Every Given = navigate to a URL. Every When = click/fill/select a UI element. "
    "Every Then = assert visible text, badge, banner, or flash using a CSS selector or element name. "
    "BANNED: 'the system must', 'the system blocks', 'audit log created', 'status updated to'. "
    "Good Then: 'the .departure-block banner shows VESSEL DEPARTURE BLOCKED'. "
    "Good Then: 'the .alert.alert-success flash is visible'. "
    "NO login steps. Tags: @p1-safety-critical|@p2-compliance|@p3-operational "
    "+ @stcw|@mlc|@ism|@marpol|@solas|@fal + @happy-path|@boundary|@negative|@edge-case. "
    "Return Gherkin feature file text only — no markdown fences."
    + _TOOL_INSTRUCTIONS
)

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a BDD test analyst for maritime safety-critical software.

Generate Gherkin BDD scenarios that can be directly executed by a tester against the mock maritime web app at http://localhost:5000.

The mock app has these pages and UI elements:
- /crew-certs  — cert table (#certTable), status filter (#statusFilter: All/Expired/Expiring Soon/Valid), Renew button → modal (#renewModal, fields: input[name='new_expiry'], input[name='cert_number'], #renewSubmitBtn), .departure-block banner, .alert.alert-success flash, .badge-expired, .badge-expiring, .badge-valid
- /fatigue     — officer list with .badge-violation / .badge-compliant, #logRestBtn → form (select[name='officer_id'], input[name='rest_start'], input[name='rest_end']), .btn-outline-warning reassign, .departure-block banner
- /incidents   — incident list with .badge-high/medium/low, [data-bs-target="#newIncidentModal"] → #newIncidentModal (select[name='type/severity/vessel'], input[name='location'], textarea[name='description'], #reportIncidentBtn), Review → #reviewModal (#notifyAuthority, #submitReviewBtn), .departure-block banner
- /voyage      — #voyageTable, [data-bs-target="#newVoyageModal"] → #newVoyageModal (select[name='vessel/fuel_type'], input[name='departure_port/arrival_port/departure_date/speed_kts/bunker_qty/distance_nm'], #createVoyageBtn), .departure-block banner, .badge.bg-warning.text-dark (ECA badge), button[onclick^="showVoyageDetails"] → #voyageDetailCard (#confirmDeviationBtn, #weather-deviation-alert), .alert.alert-success flash

CRITICAL RULES:
0. NO LOGIN STEPS. No authentication exists. Every scenario begins: Given the user navigates to "http://localhost:5000/[page]"
1. Generate 8-12 scenarios — P1 safety-critical first, Scenario Outline for boundaries
2. EVERY Given step = navigate to a URL. EVERY When step = click a button, fill a field, select an option. EVERY Then step = assert visible text, badge, banner, or flash message using a real CSS selector or element name from the list above.
3. BANNED phrases — NEVER write these:
   - "the system must block / the system blocks / the system displays"
   - "an audit log is created / the status is updated to / the system flags"
   - "the navigator attempts / the plan must cover / the system checks"
   Instead: assert what the USER SEES — a banner text, a badge colour, a flash message, a disabled button.
4. GOOD step examples:
   - Given the user navigates to "http://localhost:5000/voyage"
   - When the user clicks the Plan New Voyage button
   - When the user fills bunker_qty with "0" and clicks #createVoyageBtn
   - Then the .departure-block banner is visible with text "VESSEL DEPARTURE BLOCKED"
   - Then the .badge.bg-warning.text-dark shows "2 ECA"
   - Then the .alert.alert-success flash message is visible
   BAD step examples (do NOT write these):
   - Given a voyage plan is created for "VOY-2026-047"
   - Then the system must block the confirmation
   - Then an audit log entry is created
5. Tags: @p1-safety-critical|@p2-compliance|@p3-operational + @stcw|@mlc|@ism|@marpol|@solas|@fal + @happy-path|@boundary|@negative|@edge-case
6. Two-Deadline Pattern: T-30/T-0/T+1 in ONE Scenario Outline
7. Block-Override-Audit: .departure-block visible → user takes action → .alert.alert-success confirms → .departure-block gone

Return Gherkin feature file text only. No prose, no markdown fencing."""


class TestStrategistAgent:
    """Agent 2 — BDD Gherkin generation with maritime safety patterns."""

    name = "Test Strategist"

    def __init__(self, log_callback: Callable[[str], None] | None = None) -> None:
        self._log  = log_callback or log.info
        self._app_kb = self._load_app_kb()

    @staticmethod
    def _load_app_kb():
        try:
            from memory.app_features_kb import AppFeaturesKB
            return AppFeaturesKB()
        except Exception:
            return None

    def _build_app_section(self, feature_name: str) -> str:
        """Query App KB and return a compact required-workflows block for the user message."""
        if not self._app_kb:
            return ""
        try:
            app = self._app_kb.query(feature_name)
            if not app:
                return ""
            workflows = "\n".join(f"  {i+1}. {w}" for i, w in enumerate(app["workflows"]))
            states    = "\n".join(f"  - {s}" for s in app["testable_states"][:5])
            return (
                f"\nREQUIRED — write exactly ONE distinct scenario per workflow and "
                f"one per testable state below. Do NOT repeat or combine them:\n"
                f"Workflows (each must become its own scenario):\n{workflows}\n"
                f"Testable states (each must become its own scenario):\n{states}"
            )
        except Exception:
            return ""

    def generate(
        self,
        feature_name: str,
        feature_description: str,
        domain_analysis: dict,
    ) -> dict:
        self._log(f"[{self.name}] Generating Gherkin for: {feature_name}")

        enrichment = {
            "regulations": domain_analysis.get("applicable_regulations", [])[:6],
            "p1_reqs":     domain_analysis.get("p1_safety_requirements", [])[:5],
            "boundaries":  domain_analysis.get("boundary_values", [])[:6],
            "psc":         domain_analysis.get("psc_detention_triggers", [])[:4],
            "edge_cases":  domain_analysis.get("mandatory_edge_cases", [])[:4],
        }

        app_section = self._build_app_section(feature_name)
        if app_section:
            self._log(f"[{self.name}] App KB workflows injected into user message")

        user_msg = f"""Generate Gherkin BDD scenarios for: {feature_name}

Requirements:
{feature_description[:1000]}

Domain Data (use these exact values in scenarios):
Regulations: {', '.join(enrichment['regulations'])}
P1 Safety Requirements: {'; '.join(enrichment['p1_reqs'])}
Boundary Values: {'; '.join(enrichment['boundaries'])}
PSC Detention Triggers: {'; '.join(enrichment['psc'])}
Mandatory Edge Cases: {'; '.join(enrichment['edge_cases'])}
{app_section}

Apply Two-Deadline Pattern (use Scenario Outline), Block-Override-Audit Pattern.
Generate 8-12 scenarios. P1 safety-critical scenarios first."""

        self._log(f"[{self.name}] Calling LLM with tool-calling (90s timeout)…")
        gherkin_text = ""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(
                    llm.complete_with_tools,
                    _TOOL_SYSTEM_PROMPT,   # compact prompt — avoids 413 on long inputs
                    user_msg,
                    [_VALIDATE_SCHEMA],
                    2000,
                    dispatch,
                )
                raw = future.result(timeout=90)
            gherkin_text = self._extract_gherkin(raw)
            if gherkin_text:
                self._log(f"[{self.name}] Tool-calling path succeeded")
        except Exception as exc:
            self._log(f"[{self.name}] Tool-calling failed ({type(exc).__name__}: {exc}) — falling back to complete_gen")

        if not gherkin_text:
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(llm.complete_gen, SYSTEM_PROMPT, user_msg, 2000)
                    raw = future.result(timeout=45)
                gherkin_text = self._extract_gherkin(raw)
            except Exception as exc:
                self._log(f"[{self.name}] LLM fallback failed ({exc}) — using template")
                gherkin_text = self._template_gherkin(feature_name, domain_analysis)

        validation   = validate_gherkin(gherkin_text)
        review_loops = 0

        # ── Single review pass if output quality is low ──────────────────────
        needs_review = (
            validation["scenario_count"] < 6
            or validation["safety_tagged_count"] < 2
        )
        if needs_review:
            self._log(
                f"[{self.name}] Review triggered — "
                f"{validation['scenario_count']} scenarios, "
                f"{validation['safety_tagged_count']} safety-tagged (thresholds: 6, 2)"
            )
            review_msg = (
                f"The previous output had only {validation['scenario_count']} scenarios "
                f"and {validation['safety_tagged_count']} @p1-safety-critical tags — below minimum.\n\n"
                f"Regenerate with at least 8 scenarios. "
                f"Mark P1 safety-critical first. No login steps.\n\n"
                + user_msg
            )
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(llm.complete_gen, SYSTEM_PROMPT, review_msg, 2000)
                    revised_raw = future.result(timeout=45)
                revised_text = self._extract_gherkin(revised_raw)
                revised_val  = validate_gherkin(revised_text)
                if revised_val["scenario_count"] >= validation["scenario_count"]:
                    gherkin_text = revised_text
                    validation   = revised_val
                review_loops = 1
                self._log(
                    f"[{self.name}] Review complete — "
                    f"{validation['scenario_count']} scenarios after review"
                )
            except Exception as exc:
                self._log(f"[{self.name}] Review loop failed ({exc}) — keeping original")

        self._log(
            f"[{self.name}] Complete — {validation['scenario_count']} scenarios, "
            f"{validation['safety_tagged_count']} safety-tagged, "
            f"{review_loops} review loop(s)"
        )

        safe_name = feature_name.lower().replace(" ", "_")
        dispatch("write_test_file", {"filename": safe_name, "content": gherkin_text, "file_type": "feature"})

        return {
            "feature_name":    feature_name,
            "gherkin_text":    gherkin_text,
            "validation":      validation,
            "review_loops":    review_loops,
            "review_history":  [],
            "scenario_titles": [s["title"] for s in validation.get("scenarios", [])],
            "scenario_count":  validation["scenario_count"],
        }

    @staticmethod
    def _extract_gherkin(text: str) -> str:
        if "Feature:" in text:
            return text[text.find("Feature:"):].strip()
        import re
        m = re.search(r"```(?:gherkin|cucumber)?\n([\s\S]*?)```", text)
        return m.group(1).strip() if m else text.strip()

    @staticmethod
    def _template_gherkin(feature_name: str, domain: dict) -> str:
        regs = domain.get("applicable_regulations", ["solas"])[:3]
        reg_tags = " ".join(f"@{r.split()[0].lower()}" for r in regs)
        risk  = domain.get("risk_level", "MEDIUM").upper()
        p1tag = "@p1-safety-critical" if risk == "HIGH" else "@p2-compliance"

        slug = feature_name.lower().replace(" ", "-")
        return f"""Feature: {feature_name}

  {p1tag} {reg_tags} @happy-path
  Scenario: Valid {feature_name.lower()} record allows vessel departure
    Given the user navigates to the {slug} page
    And the compliance status shows all records as valid
    When the departure check banner is inspected
    Then no departure-block banner is visible
    And no expiry alerts are displayed

  {p1tag} {reg_tags} @negative
  Scenario: Expired {feature_name.lower()} record blocks vessel departure
    Given the user navigates to the {slug} page
    And at least one record shows an "Expired" status badge
    When the departure-block banner is checked
    Then the "VESSEL DEPARTURE BLOCKED" banner is visible
    And the banner text identifies the expired record

  @p2-compliance {reg_tags} @boundary
  Scenario Outline: {feature_name} expiry warning at threshold boundaries
    Given the user navigates to the {slug} page
    And a record expires in <days_to_expiry> days
    When the compliance summary is viewed
    Then <expected_alert> is displayed
    Examples:
      | days_to_expiry | expected_alert               |
      | 31             | no alert                     |
      | 30             | EXPIRY ALERT warning banner  |
      | 7              | EXPIRY ALERT warning banner  |
      | 0              | VESSEL DEPARTURE BLOCKED banner |
      | -1             | VESSEL DEPARTURE BLOCKED banner |

  @p1-safety-critical {reg_tags} @edge-case
  Scenario: Renewing an expired record clears the departure block
    Given the user navigates to the {slug} page
    And the "VESSEL DEPARTURE BLOCKED" banner is visible
    When the user clicks the Renew button for the expired record
    And fills in a valid future expiry date in the renewal modal
    And clicks the Submit button
    Then the success flash message is displayed
    And the departure-block banner is no longer visible
"""

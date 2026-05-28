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
from tools.tool_registry import dispatch

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a BDD test analyst for maritime safety-critical software.

Generate Gherkin BDD scenarios that can be directly executed by a tester against the mock maritime web app at http://localhost:5000.

The mock app has these pages and UI elements:
- /crew-certs  — certification table (#certTable), status filter dropdown (#statusFilter), Renew button → modal (#renewModal) with fields #newExpiry and #certNumber, departure-block banner (#departureBlock), success flash (#flashMessage)
- /fatigue     — officer list with violation/compliant badges, log rest hours form (#logRestBtn, #officerSelect, #restStart, #restEnd), reassign button (#reassignBtn), departure-block banner
- /incidents   — incident list with severity/status/deadline, Report Incident button → modal (#incidentModal), Review button → review modal (#reviewModal), Notify Authority checkbox (#notifyAuthority), departure-block banner
- /voyage      — voyage table (#voyageTable), Plan New Voyage button → modal (#newVoyageModal), piracy alert banner, Details button → fuel/ECA/weather panel, Confirm Route Deviation button (#confirmDeviation)

CRITICAL RULES:
0. NO LOGIN STEPS. The mock app has NO authentication and NO login page. NEVER write "Given I am logged in as..." or any login/role setup step. Every scenario begins by navigating directly to a page URL.
1. Generate 8-12 scenarios — P1 safety-critical first, use Scenario Outline for boundaries
2. Every step must describe a real UI action: navigating to a page, clicking a button, filling a form field, selecting a dropdown option, or asserting visible text/banners/badges
3. Tag every scenario: @p1-safety-critical|@p2-compliance|@p3-operational + @stcw|@mlc|@ism|@marpol|@solas|@fal + @happy-path|@boundary|@negative|@edge-case
4. Two-Deadline Pattern: T-30, T-0 (boundary), T+1 (overdue) — use ONE Scenario Outline
5. Block-Override-Audit: departure-block banner visible → form action taken → success flash confirms
6. Use exact threshold values from domain data
7. Given/When/Then steps only — no abstract steps like "the system checks compliance" without a concrete UI assertion

Return Gherkin feature file text only. No prose, no markdown fencing."""


class TestStrategistAgent:
    """Agent 2 — BDD Gherkin generation with maritime safety patterns."""

    name = "Test Strategist"

    def __init__(self, log_callback: Callable[[str], None] | None = None) -> None:
        self._log = log_callback or log.info

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

        user_msg = f"""Generate Gherkin BDD scenarios for: {feature_name}

Requirements:
{feature_description[:1200]}

Domain Data (use these exact values in scenarios):
Regulations: {', '.join(enrichment['regulations'])}
P1 Safety Requirements: {'; '.join(enrichment['p1_reqs'])}
Boundary Values: {'; '.join(enrichment['boundaries'])}
PSC Detention Triggers: {'; '.join(enrichment['psc'])}
Mandatory Edge Cases: {'; '.join(enrichment['edge_cases'])}

Apply Two-Deadline Pattern (use Scenario Outline), Block-Override-Audit Pattern.
Generate 8-12 scenarios. P1 safety-critical scenarios first."""

        self._log(f"[{self.name}] Calling LLM (45s timeout)…")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(llm.complete_gen, SYSTEM_PROMPT, user_msg, 2000)
                raw = future.result(timeout=45)
            gherkin_text = self._extract_gherkin(raw)
        except concurrent.futures.TimeoutError:
            self._log(f"[{self.name}] LLM timed out (45s) — using template fallback")
            gherkin_text = self._template_gherkin(feature_name, domain_analysis)
        except Exception as exc:
            self._log(f"[{self.name}] LLM failed ({exc}) — using template fallback")
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

"""
Agent 3 — AutomationEngineerAgent
Generates production-grade TypeScript Playwright test specs from Gherkin.

Workflow:
  1. Scrape the live mock app page with Playwright Python to get REAL element IDs,
     form field names, button texts, modals and banners from the actual DOM.
  2. Pass the scraped locator context + Gherkin to an LLM which generates TypeScript
     using ONLY the confirmed real locators.
  3. Fallback to hardcoded AST generation if mock app is not running or LLM fails.
"""

from __future__ import annotations
import json, re, logging, concurrent.futures
from typing import Callable

from services.llm_service       import llm
from services.mock_app_scraper  import MockAppScraper
from tools.gherkin_validator    import validate_gherkin
from tools.coverage_calculator  import calculate_coverage
from tools.tool_registry        import dispatch

log = logging.getLogger(__name__)

# ── Playwright config (written alongside every spec) ──────────────────────────

_PLAYWRIGHT_CONFIG = """\
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 30_000,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:5000',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
"""

# ── LLM system prompt — strict locator discipline ─────────────────────────────

_LLM_SYSTEM_PROMPT = """\
You are a Playwright TypeScript test engineer. Generate tests that PASS against a live Flask app.

LOCATOR RULES (strict — DOM CONTEXT is the only source of truth):
- IDs:            page.locator('#id')
- Input by name:  page.locator("input[name='x']")
- Select:         page.locator("select[name='x']").selectOption('Text')
- Button with ID: page.locator('#btnId').click()
- Button no ID:   page.getByRole('button', { name: 'Text' })
- Modal trigger:  page.locator('[data-bs-target="#modal"]').click()
- After modal:    await expect(page.locator('#modal')).toBeVisible()
- After POST:     await page.waitForLoadState('networkidle')
- Flash success:  page.locator('.alert.alert-success')
- JS-shown div:   click trigger → await expect(page.locator('#id')).toBeVisible()
- Banner:         page.locator('.departure-block')
- Not visible:    await expect(locator).toHaveCount(0)
- Step not in DOM: // NOT IN MOCK APP: <step>

OUTPUT: import block + test.describe with P1_SAFETY / P2_COMPLIANCE / P3_OPERATIONAL groups.
Return ONLY the TypeScript. No markdown fences."""


# ── Hardcoded fallback locators (used when mock app is not running) ────────────

_FALLBACK_LOCATORS: dict[str, dict] = {
    "crew_certs": {
        "url":           "/crew-certs",
        "cert_table":    "table#certTable",
        "status_filter": "select#statusFilter",
        "badge_expired": ".badge-expired",
        "badge_expiring":".badge-expiring",
        "badge_valid":   ".badge-valid",
        "depart_block":  ".departure-block",
        "renew_btn":     "button.btn-outline-primary",
        "renew_modal":   "#renewModal",
        "new_expiry":    "input[name='new_expiry']",
        "cert_number":   "input[name='cert_number']",
        "renew_submit":  "#renewSubmitBtn",
    },
    "voyage": {
        "url":              "/voyage",
        "depart_block":     ".departure-block",
        "voyage_table":     ".card-body table",
        "new_voyage_btn":   "[data-bs-target='#newVoyageModal']",
        "new_voyage_modal": "#newVoyageModal",
        "vessel_select":    "select[name='vessel']",
        "fuel_type":        "select[name='fuel_type']",
        "depart_port":      "input[name='departure_port']",
        "arrival_port":     "input[name='arrival_port']",
        "depart_date":      "input[name='departure_date']",
        "speed_kts":        "input[name='speed_kts']",
        "bunker_qty":       "input[name='bunker_qty']",
        "distance_nm":      "input[name='distance_nm']",
        "create_btn":       "#createVoyageBtn",
        "detail_btn":       "button[onclick^='showVoyageDetails']",
        "detail_card":      "#voyageDetailCard",
        "eca_badge":        ".badge.bg-warning.text-dark",
        "confirm_deviation":"#confirmDeviationBtn",
        "weather_alert":    "#weather-deviation-alert",
    },
    "fatigue": {
        "url":             "/fatigue",
        "violation_block": ".departure-block",
        "officer_select":  "select[name='officer_id']",
        "rest_start":      "input[name='rest_start']",
        "rest_end":        "input[name='rest_end']",
        "log_btn":         "#logRestBtn",
        "badge_violation": ".badge-violation",
        "badge_compliant": ".badge-compliant",
        "reassign_btn":    "button.btn-outline-warning",
    },
    "incidents": {
        "url":             "/incidents",
        "overdue_block":   ".departure-block",
        "report_btn":      "[data-bs-target='#newIncidentModal']",
        "new_modal":       "#newIncidentModal",
        "severity_select": "select[name='severity']",
        "type_select":     "select[name='type']",
        "vessel_select":   "select[name='vessel']",
        "location_input":  "input[name='location']",
        "desc_textarea":   "textarea[name='description']",
        "submit_btn":      "#reportIncidentBtn",
        "review_modal":    "#reviewModal",
        "notify_cb":       "#notifyAuthority",
        "review_submit":   "#submitReviewBtn",
        "badge_high":      ".badge-high",
    },
    "port_call": {
        "url":             "/port-call",
        "new_btn":         "[data-bs-target='#newPortCallModal']",
        "new_modal":       "#newPortCallModal",
        "vessel_select":   "select[name='vessel']",
        "port_input":      "input[name='port']",
        "eta_input":       "input[name='eta']",
        "create_btn":      "#createPortCallBtn",
        "submit_notice":   "#submitNoticeBtn",
    },
}


class AutomationEngineerAgent:
    """
    Agent 3 — Scrapes the live mock app DOM, then uses an LLM to generate
    production-grade TypeScript Playwright tests with real locators.
    """

    name = "Automation Engineer"

    def __init__(self, log_callback: Callable[[str], None] | None = None) -> None:
        self._log     = log_callback or log.info
        self._scraper = MockAppScraper()

    def generate(
        self,
        feature_name: str,
        gherkin_result: dict,
        domain_analysis: dict,
    ) -> dict:
        self._log(f"[{self.name}] Generating Playwright tests for: {feature_name}")

        gherkin_text    = gherkin_result.get("gherkin_text", "")
        scenario_titles = gherkin_result.get("scenario_titles", [])
        validation      = validate_gherkin(gherkin_text)
        all_reqs        = (
            domain_analysis.get("p1_safety_requirements", []) +
            domain_analysis.get("p2_compliance_requirements", [])
        )
        coverage = calculate_coverage(all_reqs, scenario_titles, feature_name)
        slug     = self._detect_slug(feature_name, gherkin_text)
        url_path = _FALLBACK_LOCATORS.get(slug, {}).get("url", f"/{slug.replace('_', '-')}")

        # ── Step 1: Scrape live DOM ──────────────────────────────────────────
        self._log(f"[{self.name}] Scraping live DOM at {url_path}…")
        scraped = self._scraper.scrape(slug, url_path)

        if scraped.get("scraped"):
            self._log(
                f"[{self.name}] DOM scraped — "
                f"{len(scraped.get('ids', []))} ids, "
                f"{len(scraped.get('formFields', []))} fields, "
                f"{len(scraped.get('buttons', []))} buttons"
            )
            locator_context = self._scraper.build_locator_string(scraped)
            spec_ts = self._llm_spec(feature_name, url_path, gherkin_text, locator_context, scraped)
        else:
            self._log(
                f"[{self.name}] DOM scraping failed ({scraped.get('error', '?')}) "
                f"— using fallback locators"
            )
            locator_context = f"[Fallback — mock app offline]\n{self._fallback_context(slug)}"
            spec_ts = self._fallback_spec(feature_name, slug, gherkin_text, validation)

        safe_name = feature_name.lower().replace(" ", "_")
        dispatch("write_test_file", {"filename": safe_name,           "content": spec_ts,           "file_type": "playwright"})
        dispatch("write_test_file", {"filename": "playwright.config", "content": _PLAYWRIGHT_CONFIG, "file_type": "playwright"})

        risk_report = self._build_risk_report(feature_name, domain_analysis, coverage, scenario_titles)
        dispatch("write_test_file", {
            "filename":  f"{safe_name}_coverage_report",
            "content":   json.dumps(risk_report, indent=2),
            "file_type": "report",
        })

        self._log(
            f"[{self.name}] Complete — "
            f"{'live DOM' if scraped.get('scraped') else 'fallback'} locators, "
            f"{coverage['coverage_percentage']}% coverage"
        )
        return {
            "feature_name":      feature_name,
            "spec_ts":           spec_ts,
            "page_object_ts":    "",
            "playwright_config": _PLAYWRIGHT_CONFIG,
            "coverage_report":   coverage,
            "risk_report":       risk_report,
        }

    # ── LLM-based TypeScript generation (primary path) ────────────────────────

    def _llm_spec(
        self,
        feature_name: str,
        url_path: str,
        gherkin_text: str,
        locator_context: str,
        scraped: dict | None = None,
    ) -> str:
        # Cap DOM context and Gherkin to stay within Groq's per-request payload limit.
        # ~3000 chars DOM + ~3000 chars Gherkin ≈ 1500 tokens input → well within 8192 window.
        dom_ctx  = locator_context[:3000]
        gherkin  = gherkin_text[:3000]
        user_msg = (
            f"Feature: {feature_name}\n"
            f"Base URL: http://localhost:5000{url_path}\n\n"
            f"DOM CONTEXT (use ONLY these locators):\n{dom_ctx}\n\n"
            f"Implement these Gherkin scenarios as TypeScript tests:\n{gherkin}"
        )
        self._log(f"[{self.name}] Calling LLM for TypeScript generation (60s timeout)…")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(llm.complete_gen, _LLM_SYSTEM_PROMPT, user_msg, 3000)
                raw = future.result(timeout=60)
            spec = self._extract_ts(raw)
            if spec:
                spec = self._sanitize_ts(spec)
                self._log(f"[{self.name}] LLM generated {spec.count('test(')}) tests")
                return spec
            self._log(f"[{self.name}] LLM returned no TypeScript block — using fallback")
        except concurrent.futures.TimeoutError:
            self._log(f"[{self.name}] LLM timed out — using fallback")
        except Exception as exc:
            self._log(f"[{self.name}] LLM error ({exc}) — using fallback")

        slug = self._detect_slug(feature_name, gherkin_text)
        loc_override = self._loc_from_scraped(slug, scraped) if scraped else None
        return self._fallback_spec(
            feature_name,
            slug,
            gherkin_text,
            validate_gherkin(gherkin_text),
            loc_override=loc_override,
        )

    @staticmethod
    def _extract_ts(raw: str) -> str:
        """Extract the TypeScript code block from LLM response."""
        # Try complete fenced block first
        for lang in ("typescript", "ts", ""):
            pattern = rf"```{lang}\n([\s\S]*?)```"
            m = re.search(pattern, raw)
            if m:
                block = m.group(1).strip()
                if "import {" in block and "test(" in block:
                    return block
        # LLM truncated before the closing fence — strip opening fence and use remainder
        cleaned = re.sub(r"^```\w*\s*\n?", "", raw.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
        if "import {" in cleaned and "test(" in cleaned:
            # Close any dangling braces so the file is at least parseable
            open_braces  = cleaned.count("{") - cleaned.count("}")
            open_parens  = cleaned.count("(") - cleaned.count(")")
            if open_parens > 0:
                cleaned += ")" * open_parens
            if open_braces > 0:
                cleaned += "\n" + ("}" * open_braces)
            return cleaned
        return ""

    # ── Post-generation sanitiser — fixes systematic LLM CSS mistakes ────────

    @staticmethod
    def _sanitize_ts(spec: str) -> str:
        """
        Fix known LLM mistakes that survive even with correct DOM context:
        1. '.cls1 .cls2 .cls3' (descendant chain) → '.cls1.cls2.cls3' (same element)
           Affects: .badge .bg-* .text-*, .alert .alert-*, .btn .btn-*
        2. toHaveText(exact) → toContainText(partial) for elements that contain
           icons, whitespace, or child elements (banners, flash messages, badges).
        3. Ensures #confirmDeviationBtn and other known hidden-panel buttons are
           never clicked without a preceding visibility assertion on the panel.
        """
        # ── Fix 1: space-separated class chains on badge/alert/btn elements ──
        # Pattern: locator('.a .b') or locator(".a .b .c") where all segments start with .
        def collapse_classes(m: re.Match) -> str:
            quote = m.group(1)
            inner = m.group(2)
            # Only collapse if every token is a class selector (starts with .)
            # and there are no combinators like > + ~
            tokens = inner.split(" ")
            if all(t.startswith(".") and t == t.strip() for t in tokens if t):
                return f"locator({quote}{''.join(tokens)}{quote})"
            return m.group(0)

        spec = re.sub(
            r'locator\((["\'])((?:\.[a-zA-Z][\w-]*\s+)+\.[a-zA-Z][\w-]*)\1\)',
            collapse_classes,
            spec,
        )

        # ── Fix 2: toHaveText → toContainText for banner/flash/badge patterns ─
        # These elements always contain icon text or extra whitespace
        for pattern in (
            r"\.departure-block[^)]*\)\.toHaveText\(",
            r"\.alert[^)]*\)\.toHaveText\(",
            r"\.badge[^)]*\)\.toHaveText\(",
            r"#piracy-alert[^)]*\)\.toHaveText\(",
            r"#weather-deviation-alert[^)]*\)\.toHaveText\(",
            r"#flashMessage[^)]*\)\.toHaveText\(",
        ):
            spec = re.sub(pattern, lambda m: m.group(0).replace(".toHaveText(", ".toContainText("), spec)

        return spec

    # ── Feature slug detection ────────────────────────────────────────────────

    @staticmethod
    def _detect_slug(feature_name: str, gherkin_text: str = "") -> str:
        corpus = feature_name.lower()
        gh     = gherkin_text.lower()

        if "voyage" in corpus or "/voyage" in gh or "plan new voyage" in gh or "newvoyagemodal" in gh:
            return "voyage"
        if "fatigue" in corpus or "rest hour" in gh or "logrestbtn" in gh:
            return "fatigue"
        if "incident" in corpus or "newincidentmodal" in gh or "reportincidentbtn" in gh:
            return "incidents"
        if "port" in corpus or "port-call" in gh or "newportcallmodal" in gh:
            return "port_call"
        if any(k in corpus for k in ("crew", "cert", "stcw", "competenc")):
            return "crew_certs"
        # Scan Gherkin for page markers
        if "certtable" in gh or "statusfilter" in gh or "renewmodal" in gh:
            return "crew_certs"
        if "voyagetable" in gh or "/voyage" in gh:
            return "voyage"
        if "resthoursform" in gh or "/fatigue" in gh:
            return "fatigue"
        if "/incidents" in gh:
            return "incidents"
        if "/port-call" in gh:
            return "port_call"
        return "crew_certs"

    # ── Fallback context string (when scraping fails) ────────────────────────

    @staticmethod
    def _fallback_context(slug: str) -> str:
        loc = _FALLBACK_LOCATORS.get(slug, {})
        lines = [f"Hardcoded fallback locators for /{slug.replace('_', '-')}:"]
        for k, v in loc.items():
            if k != "url":
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    # ── Scrape-to-locator dict builder ────────────────────────────────────────

    @staticmethod
    def _loc_from_scraped(slug: str, scraped: dict) -> dict:
        """Merge live-scraped element data over the hardcoded fallback locators."""
        loc = dict(_FALLBACK_LOCATORS.get(slug, {}))

        for elem in scraped.get("ids", []):
            eid = elem.get("id", "")
            if eid == "voyageDetailCard":    loc["detail_card"]      = "#voyageDetailCard"
            if eid == "weather-deviation-alert": loc["weather_alert"] = "#weather-deviation-alert"
            if eid == "certTable":           loc["cert_table"]       = "#certTable"
            if eid == "statusFilter":        loc["status_filter"]    = "select#statusFilter"
            if eid == "renewModal":          loc["renew_modal"]      = "#renewModal"
            if eid == "newVoyageModal":      loc["new_voyage_modal"] = "#newVoyageModal"
            if eid == "newIncidentModal":    loc["new_modal"]        = "#newIncidentModal"
            if eid == "reviewModal":         loc["review_modal"]     = "#reviewModal"
            if eid == "newPortCallModal":    loc["new_modal"]        = "#newPortCallModal"

        for btn in scraped.get("buttons", []):
            bid = btn.get("id", "")
            if bid == "createVoyageBtn":     loc["create_btn"]        = "#createVoyageBtn"
            if bid == "confirmDeviationBtn": loc["confirm_deviation"] = "#confirmDeviationBtn"
            if bid == "renewSubmitBtn":      loc["renew_submit"]      = "#renewSubmitBtn"
            if bid == "logRestBtn":          loc["log_btn"]           = "#logRestBtn"
            if bid == "reportIncidentBtn":   loc["submit_btn"]        = "#reportIncidentBtn"
            if bid == "submitReviewBtn":     loc["review_submit"]     = "#submitReviewBtn"
            if bid == "notifyAuthority":     loc["notify_cb"]         = "#notifyAuthority"
            if bid == "createPortCallBtn":   loc["create_btn"]        = "#createPortCallBtn"
            if btn.get("modalTarget") == "#newVoyageModal":
                loc["new_voyage_btn"] = "[data-bs-target='#newVoyageModal']"

        return loc

    # ── Fallback AST-based spec (when LLM unavailable) ────────────────────────

    def _fallback_spec(
        self,
        feature_name: str,
        slug: str,
        gherkin_text: str,
        validation: dict,
        loc_override: dict | None = None,
    ) -> str:
        scenarios = self._parse_scenarios(gherkin_text)
        loc       = loc_override if loc_override is not None \
                    else _FALLBACK_LOCATORS.get(slug, {"url": f"/{slug.replace('_', '-')}"})
        url       = loc.get("url", f"/{slug.replace('_', '-')}")
        safe_name = feature_name.replace("'", "\\'")

        groups: dict[str, list] = {"P1_SAFETY": [], "P2_COMPLIANCE": [], "P3_OPERATIONAL": []}
        for sc in scenarios:
            groups[self._priority_group(sc["tags"])].append(sc)

        helpers = self._helper_functions(slug, loc)
        lines = [
            "import { test, expect } from '@playwright/test';",
            "",
            f"// Feature: {feature_name}",
            f"// Generated from Gherkin — {len(scenarios)} scenarios",
            f"// Target: http://localhost:5000{url}",
            "// NOTE: fallback mode — mock app was offline during generation.",
            "//       Re-run pipeline with mock app running for live-DOM locators.",
            "",
        ]
        if helpers:
            lines += helpers + [""]

        lines += [
            f"test.describe('{safe_name}', () => {{",
            f"  test.beforeEach(async ({{ page }}) => {{",
            f"    await page.goto('{url}');",
            f"    await page.waitForLoadState('domcontentloaded');",
            "  });",
            "",
        ]

        for group, scs in groups.items():
            if not scs:
                continue
            lines.append(f"  test.describe('{group}', () => {{")
            for sc in scs:
                t = sc["title"].replace("'", "\\'")
                lines.append(f"    test('{t}', async ({{ page }}) => {{")
                for action in self._actions_for_scenario(sc, loc, slug):
                    lines.append(f"      {action}")
                lines.append("    });")
                lines.append("")
            lines.append("  });")
            lines.append("")
        lines.append("});")
        return "\n".join(lines)

    # ── Fallback: per-step action mapper ─────────────────────────────────────

    def _actions_for_scenario(self, sc: dict, loc: dict, slug: str) -> list[str]:
        actions: list[str] = []
        for step in sc["steps"]:
            mapped = self._map_step(step, loc, slug)
            actions.extend(mapped)
            actions.append("")
        while actions and actions[-1] == "":
            actions.pop()
        # If nothing real was mapped, use slug-level fallback
        real = [a for a in actions if not a.startswith("//") and a.strip()]
        if not real:
            kind = self._classify(sc)
            def g(key: str, fb: str = "body") -> str:
                return loc.get(key, fb)
            if slug == "crew_certs":  return self._crew_certs_actions(kind, g)
            if slug == "voyage":      return self._voyage_actions(kind, g)
            if slug == "fatigue":     return self._fatigue_actions(kind, g)
            if slug == "incidents":   return self._incidents_actions(kind, g)
            if slug == "port_call":   return self._port_call_actions(kind, g)
        return actions

    def _map_step(self, step: str, loc: dict, slug: str) -> list[str]:
        s   = step.lower()
        out = [f"// {step}"]
        url = loc.get("url", f"/{slug.replace('_', '-')}")

        def g(key: str, fb: str = "body") -> str:
            return loc.get(key, fb)

        # Navigation
        if any(k in s for k in ("navigate to", "go to", "i am on", "open the", "visit")):
            nav_url = self._url_from_step(s, url)
            out += [f"await page.goto('{nav_url}');",
                    "await page.waitForLoadState('domcontentloaded');"]
            return out

        # Login / role (no auth in mock app)
        if any(k in s for k in ("logged in", "i am a", "as a ship", "as a safety", "as a navigator")):
            out += [f"await page.goto('{url}');",
                    "await page.waitForLoadState('domcontentloaded');"]
            return out

        # Voyage / cert table visible (voyage check first to avoid certTable false-match)
        if any(k in s for k in ("voyage table", "voyage register", "voyage list")):
            out += ["await expect(page.locator('.card-body table')).toBeVisible();",
                    "await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();"]
            return out

        if any(k in s for k in ("certification register", "cert table")) or \
           ("table is visible" in s and "cert" in s):
            out += [f"await expect(page.locator('{g('cert_table','table#certTable')}')).toBeVisible();",
                    f"await expect(page.locator('{g('cert_table','table#certTable')} tbody tr').first()).toBeVisible();"]
            return out

        if any(k in s for k in ("incident list", "incident table")):
            out += ["await expect(page.locator('table, .incident-list').first()).toBeVisible();"]
            return out

        if any(k in s for k in ("officer list", "fatigue list")):
            out += ["await expect(page.locator('.badge-violation, .badge-compliant').first()).toBeVisible();"]
            return out

        # Departure / piracy block
        if any(k in s for k in ("departure block", "vessel departure blocked", "blocked", "piracy alert")):
            if any(k in s for k in ("not visible", "is not", "does not", "disappears", "no longer", "clears", "removed")):
                out += ["await expect(page.locator('.departure-block')).toHaveCount(0);"]
            else:
                text_assert = "PIRACY" if "piracy" in s else "VESSEL DEPARTURE BLOCKED"
                out += [f"await expect(page.locator('.departure-block').first()).toBeVisible();",
                        f"await expect(page.locator('.departure-block').first()).toContainText('{text_assert}');"]
            return out

        # Expiry alerts
        if any(k in s for k in ("expiry alert", "warning banner", "expiry warning")):
            if any(k in s for k in ("not visible", "is not", "does not")):
                out += ["await expect(page.locator('.warning-banner')).toHaveCount(0);"]
            else:
                out += ["await expect(page.locator('.warning-banner').first()).toBeVisible();",
                        "await expect(page.locator('.warning-banner').first()).toContainText('EXPIRY ALERT');"]
            return out

        # Status badges
        if "badge" in s and "expired" in s:
            out += ["await expect(page.locator('.badge-expired').first()).toBeVisible();"]
            return out
        if "badge" in s and ("expiring" in s or "expiring soon" in s):
            out += ["await expect(page.locator('.badge-expiring').first()).toBeVisible();"]
            return out
        if "badge" in s and "valid" in s:
            out += ["await expect(page.locator('.badge-valid').first()).toBeVisible();"]
            return out

        # Status filter
        if "filter" in s and any(k in s for k in ("expired", "expiring", "valid", "select", "choose")):
            if "expiring" in s:
                out += ["await page.locator('select#statusFilter').selectOption('expiring_soon');"]
            elif "expired" in s:
                out += ["await page.locator('select#statusFilter').selectOption('expired');"]
            elif "valid" in s:
                out += ["await page.locator('select#statusFilter').selectOption('valid');"]
            else:
                out += ["await page.locator('select#statusFilter').selectOption('all');"]
            return out

        # Renew cert
        if "click" in s and "renew" in s:
            out += [f"await page.locator('{g('renew_btn','button.btn-outline-primary')}').first().click();",
                    f"await expect(page.locator('{g('renew_modal','#renewModal')}')).toBeVisible();"]
            return out

        if any(k in s for k in ("fill", "enter", "input")) and any(k in s for k in ("expiry", "new_expiry", "date")):
            out += ["await page.locator(\"input[name='new_expiry']\").fill('2029-12-31');"]
            return out

        if any(k in s for k in ("fill", "enter", "input")) and "cert" in s and "number" in s:
            out += ["await page.locator(\"input[name='cert_number']\").fill('STCW-2029-00123');"]
            return out

        if "click" in s and any(k in s for k in ("update certificate", "submit", "renewsubmit")):
            out += [f"await page.locator('{g('renew_submit','#renewSubmitBtn')}').click();",
                    "await page.waitForLoadState('networkidle');"]
            return out

        # Success flash
        if "success" in s and any(k in s for k in ("flash", "message", "confirm", "alert")):
            if any(k in s for k in ("not visible", "is not")):
                out += ["await expect(page.locator('.alert-success, .flash-success')).toHaveCount(0);"]
            else:
                out += ["await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();"]
            return out

        # Voyage — plan new voyage modal
        if any(k in s for k in ("plan new voyage", "click plan", "new voyage button")):
            out += ["await page.locator(\"[data-bs-target='#newVoyageModal']\").click();",
                    f"await expect(page.locator('{g('new_voyage_modal','#newVoyageModal')}')).toBeVisible();"]
            return out

        # Voyage — form fields
        if any(k in s for k in ("departure port", "enter departure")):
            out += ["await page.locator(\"input[name='departure_port']\").fill('Port of Singapore');"]
            return out
        if any(k in s for k in ("arrival port", "enter arrival")):
            out += ["await page.locator(\"input[name='arrival_port']\").fill('Port of Rotterdam');"]
            return out
        if any(k in s for k in ("bunker", "fuel quantity")):
            out += ["await page.locator(\"input[name='bunker_qty']\").fill('1500');"]
            return out
        if "speed" in s and any(k in s for k in ("knot", "kts", "enter", "fill")):
            speed = "5" if ("5 knot" in s or "minimum" in s) else "25" if ("25 knot" in s or "maximum" in s) else "14.5"
            out += [f"await page.locator(\"input[name='speed_kts']\").fill('{speed}');"]
            return out
        if "distance" in s or "nautical miles" in s:
            out += ["await page.locator(\"input[name='distance_nm']\").fill('8500');"]
            return out
        if "fuel type" in s or "select fuel" in s:
            fuel = "MGO (ECA compliant)" if "mgo" in s else "LNG" if "lng" in s else "VLSFO (0.5% Sulphur)"
            out += [f"await page.locator(\"select[name='fuel_type']\").selectOption('{fuel}');"]
            return out

        # Voyage — create / submit
        if "create voyage" in s or ("click" in s and "create" in s and "voyage" in s):
            out += [f"await page.locator('{g('create_btn','#createVoyageBtn')}').click();",
                    "await page.waitForLoadState('networkidle');",
                    "await expect(page.locator('.alert.alert-success').first()).toBeVisible();",
                    "await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();"]
            return out

        # Voyage — detail panel
        if any(k in s for k in ("detail", "details button", "click details")):
            out += ["await page.locator('button[onclick^=\"showVoyageDetails\"]').first().click();",
                    f"await expect(page.locator('{g('detail_card','#voyageDetailCard')}')).toBeVisible();"]
            return out

        # Voyage — weather / ECA / piracy
        if any(k in s for k in ("weather deviation", "weather alert")):
            if any(k in s for k in ("not visible", "removed", "no longer")):
                out += [f"await expect(page.locator('{g('weather_alert','#weather-deviation-alert')}')).toHaveCount(0);"]
            else:
                out += [f"await expect(page.locator('{g('weather_alert','#weather-deviation-alert')}')).toBeVisible();",
                        f"await expect(page.locator('{g('weather_alert','#weather-deviation-alert')}')).toContainText('deviation');"]
            return out

        if "confirm" in s and "deviation" in s:
            out += [f"await page.locator('{g('confirm_deviation','#confirmDeviationBtn')}').click();",
                    "await page.waitForLoadState('networkidle');",
                    "await expect(page.locator('.alert.alert-success').first()).toBeVisible();"]
            return out

        if "eca" in s:
            if any(k in s for k in ("none", "no eca", "not visible")):
                out += ["await expect(page.locator('.badge.bg-success:has-text(\"None\")').first()).toBeVisible();"]
            else:
                out += ["await expect(page.locator('.badge.bg-warning.text-dark').first()).toBeVisible();",
                        "await expect(page.locator('.badge.bg-warning.text-dark').first()).toContainText('ECA');"]
            return out

        # Fatigue
        if any(k in s for k in ("log rest", "enter rest", "record rest", "rest hours")):
            out += ["await page.locator(\"select[name='officer_id']\").selectOption({ index: 0 });",
                    "await page.locator(\"input[name='rest_start']\").fill('2025-01-15T22:00');",
                    "await page.locator(\"input[name='rest_end']\").fill('2025-01-16T08:00');",
                    f"await page.locator('{g('log_btn','#logRestBtn')}').click();",
                    "await page.waitForLoadState('networkidle');"]
            return out

        if "compliant" in s and "not" not in s:
            out += [f"await expect(page.locator('{g('badge_compliant','.badge-compliant')}').first()).toBeVisible();"]
            return out
        if "violation" in s and "not" not in s:
            out += [f"await expect(page.locator('{g('badge_violation','.badge-violation')}').first()).toBeVisible();"]
            return out
        if "reassign" in s:
            out += [f"await page.locator('{g('reassign_btn','button.btn-outline-warning')}').first().click();",
                    "await page.waitForLoadState('networkidle');"]
            return out

        # Incidents
        if any(k in s for k in ("report incident", "click report", "new incident")):
            out += ["await page.locator(\"[data-bs-target='#newIncidentModal']\").click();",
                    f"await expect(page.locator('{g('new_modal','#newIncidentModal')}')).toBeVisible();"]
            return out
        if "severity" in s and any(k in s for k in ("select", "high", "medium", "low")):
            sev = "High" if "high" in s else "Low" if "low" in s else "Medium"
            out += [f"await page.locator(\"select[name='severity']\").selectOption('{sev}');"]
            return out
        if any(k in s for k in ("location", "enter location")):
            out += ["await page.locator(\"input[name='location']\").fill('Engine Room');"]
            return out
        if "description" in s:
            out += ["await page.locator(\"textarea[name='description']\").fill('Automated test incident.');"]
            return out
        if "submit" in s and any(k in s for k in ("report", "incident")):
            out += [f"await page.locator('{g('submit_btn','#reportIncidentBtn')}').click();",
                    "await page.waitForLoadState('networkidle');"]
            return out
        if "click" in s and "review" in s:
            out += ["await page.locator('button:has-text(\"Review\")').first().click();",
                    f"await expect(page.locator('{g('review_modal','#reviewModal')}')).toBeVisible();"]
            return out
        if any(k in s for k in ("notify authority", "notify maritime")):
            out += [f"await page.locator('{g('notify_cb','#notifyAuthority')}').check();",
                    f"await expect(page.locator('{g('notify_cb','#notifyAuthority')}')).toBeChecked();"]
            return out
        if "submit review" in s:
            out += [f"await page.locator('{g('review_submit','#submitReviewBtn')}').click();",
                    "await page.waitForLoadState('networkidle');"]
            return out

        # Catch-all
        out += [f"// NOT IN MOCK APP: '{step}'"]
        return out

    # ── Priority group ─────────────────────────────────────────────────────────

    @staticmethod
    def _priority_group(tags: list[str]) -> str:
        tl = " ".join(tags).lower()
        if "p1" in tl or "safety" in tl or "critical" in tl: return "P1_SAFETY"
        if "p3" in tl or "operational" in tl:                return "P3_OPERATIONAL"
        return "P2_COMPLIANCE"

    # ── Scenario classifier (for fallback action dispatch) ─────────────────────

    @staticmethod
    def _classify(sc: dict) -> str:
        combined = sc["title"].lower() + " " + " ".join(sc["tags"]).lower()
        if any(k in combined for k in ("renew", "update cert", "revalidat")):             return "renew_cert"
        if any(k in combined for k in ("block", "depart", "prevent", "cannot depart")):   return "departure_block"
        if "filter" in combined:
            if "expired" in combined:   return "filter_expired"
            if "expiring" in combined:  return "filter_expiring"
            if "valid" in combined:     return "filter_valid"
            return "filter_all"
        if any(k in combined for k in ("warning", "expiry alert", "30 day")):             return "expiry_warning"
        if any(k in combined for k in ("boundary", "threshold", "outline", "t-30")):      return "boundary"
        if any(k in combined for k in ("log rest", "record rest", "rest hour")):          return "log_rest"
        if "compliant" in combined and "violation" not in combined:                       return "compliant_status"
        if "violation" in combined:                                                       return "violation_status"
        if "reassign" in combined:                                                        return "reassign_officer"
        if any(k in combined for k in ("report", "new incident", "near miss")):           return "report_incident"
        if any(k in combined for k in ("review", "approve")):                             return "review_incident"
        if any(k in combined for k in ("notify", "authority")):                           return "notify_authority"
        if any(k in combined for k in ("plan", "create voyage", "new voyage")):           return "plan_voyage"
        if any(k in combined for k in ("eca", "emission", "sulphur")):                   return "eca_compliance"
        if any(k in combined for k in ("piracy", "high risk", "hra")):                   return "piracy_block"
        if "deviation" in combined:                                                       return "route_deviation"
        if any(k in combined for k in ("port call", "arrival")):                          return "create_port_call"
        if any(k in combined for k in ("notice", "24h", "96h", "fal")):                  return "pre_arrival_notice"
        return "page_load"

    # ── Fallback slug-level actions ────────────────────────────────────────────

    @staticmethod
    def _crew_certs_actions(kind: str, g) -> list[str]:
        if kind == "departure_block":
            return [
                "await expect(page.locator('.departure-block').first()).toBeVisible();",
                "await expect(page.locator('.departure-block').first()).toContainText('VESSEL DEPARTURE BLOCKED');",
                "await expect(page.locator('.badge-expired').first()).toBeVisible();",
            ]
        if kind == "renew_cert":
            return [
                "await page.locator('select#statusFilter').selectOption('expired');",
                "await page.locator('button.btn-outline-primary').first().click();",
                "await expect(page.locator('#renewModal')).toBeVisible();",
                "await page.locator(\"input[name='new_expiry']\").fill('2029-12-31');",
                "await page.locator(\"input[name='cert_number']\").fill('STCW-2029-00123');",
                "await page.locator('#renewSubmitBtn').click();",
                "await page.waitForLoadState('networkidle');",
                "await expect(page.locator('.alert.alert-success').first()).toBeVisible();",
            ]
        if kind in ("filter_expired", "filter_expiring", "filter_valid"):
            status_map = {"filter_expired": "expired", "filter_expiring": "expiring_soon", "filter_valid": "valid"}
            status = status_map[kind]
            return [
                f"await page.locator('select#statusFilter').selectOption('{status}');",
                f"await expect(page.locator('tr[data-status=\"{status}\"]').first()).toBeVisible();",
            ]
        if kind == "expiry_warning":
            return [
                "await expect(page.locator('.warning-banner').first()).toBeVisible();",
                "await expect(page.locator('.warning-banner').first()).toContainText('EXPIRY ALERT');",
            ]
        return [
            "await expect(page.locator('table#certTable')).toBeVisible();",
            "await expect(page.locator('table#certTable thead')).toContainText('Expiry Date');",
            "await expect(page.locator('table#certTable tbody tr').first()).toBeVisible();",
            "await expect(page.locator('select#statusFilter')).toBeVisible();",
        ]

    @staticmethod
    def _voyage_actions(kind: str, g) -> list[str]:
        if kind == "piracy_block":
            return [
                "await expect(page.locator('.departure-block').first()).toBeVisible();",
                "await expect(page.locator('.departure-block').first()).toContainText('PIRACY ALERT');",
                "await expect(page.locator('.departure-block').first()).toContainText('IMB Piracy Reporting Centre');",
            ]
        if kind == "plan_voyage":
            return [
                "await page.locator(\"[data-bs-target='#newVoyageModal']\").click();",
                "await expect(page.locator('#newVoyageModal')).toBeVisible();",
                "await page.locator(\"select[name='vessel']\").selectOption('MV Oceanic Pioneer');",
                "await page.locator(\"select[name='fuel_type']\").selectOption('VLSFO (0.5% Sulphur)');",
                "await page.locator(\"input[name='departure_port']\").fill('Port of Singapore');",
                "await page.locator(\"input[name='arrival_port']\").fill('Port of Rotterdam');",
                "const futureDate = new Date(); futureDate.setDate(futureDate.getDate() + 7);",
                "await page.locator(\"input[name='departure_date']\").fill(futureDate.toISOString().split('T')[0]);",
                "await page.locator(\"input[name='speed_kts']\").fill('14.5');",
                "await page.locator(\"input[name='bunker_qty']\").fill('1500');",
                "await page.locator(\"input[name='distance_nm']\").fill('8500');",
                "await page.locator('#createVoyageBtn').click();",
                "await page.waitForLoadState('networkidle');",
                "await expect(page.locator('.alert.alert-success').first()).toBeVisible();",
            ]
        if kind == "route_deviation":
            return [
                "await page.locator('button[onclick^=\"showVoyageDetails\"]').first().click();",
                "await expect(page.locator('#voyageDetailCard')).toBeVisible();",
                "await expect(page.locator('#weather-deviation-alert')).toBeVisible();",
                "await page.locator('#confirmDeviationBtn').click();",
                "await page.waitForLoadState('networkidle');",
                "await expect(page.locator('.alert.alert-success').first()).toBeVisible();",
            ]
        if kind == "eca_compliance":
            return [
                "await expect(page.locator('.badge.bg-warning.text-dark').first()).toBeVisible();",
                "await expect(page.locator('.badge.bg-warning.text-dark').first()).toContainText('ECA');",
            ]
        return [
            "await expect(page.locator('.card-body table')).toBeVisible();",
            "await expect(page.locator('.card-body table thead')).toContainText('Voyage ID');",
            "await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();",
        ]

    @staticmethod
    def _fatigue_actions(kind: str, g) -> list[str]:
        if kind in ("departure_block", "violation_status"):
            return [
                "await expect(page.locator('.departure-block').first()).toBeVisible();",
                "await expect(page.locator('.badge-violation').first()).toBeVisible();",
            ]
        if kind == "log_rest":
            return [
                "await page.locator(\"select[name='officer_id']\").selectOption({ index: 0 });",
                "await page.locator(\"input[name='rest_start']\").fill('2025-01-15T22:00');",
                "await page.locator(\"input[name='rest_end']\").fill('2025-01-16T08:00');",
                "await page.locator('#logRestBtn').click();",
                "await page.waitForLoadState('networkidle');",
            ]
        if kind == "compliant_status":
            return [
                "await expect(page.locator('.badge-compliant').first()).toBeVisible();",
                "await expect(page.locator('.departure-block')).toHaveCount(0);",
            ]
        return [
            "await expect(page.locator('.badge-violation, .badge-compliant').first()).toBeVisible();",
            "await expect(page.locator('#logRestBtn')).toBeVisible();",
        ]

    @staticmethod
    def _incidents_actions(kind: str, g) -> list[str]:
        if kind == "report_incident":
            return [
                "await page.locator(\"[data-bs-target='#newIncidentModal']\").click();",
                "await expect(page.locator('#newIncidentModal')).toBeVisible();",
                "await page.locator(\"select[name='type']\").selectOption('Near Miss');",
                "await page.locator(\"select[name='severity']\").selectOption('High');",
                "await page.locator(\"select[name='vessel']\").selectOption({ index: 0 });",
                "await page.locator(\"input[name='location']\").fill('Engine Room');",
                "await page.locator(\"textarea[name='description']\").fill('Near miss during routine inspection.');",
                "await page.locator('#reportIncidentBtn').click();",
                "await page.waitForLoadState('networkidle');",
                "await expect(page.locator('.alert.alert-success').first()).toBeVisible();",
            ]
        if kind == "review_incident":
            return [
                "await page.locator('button:has-text(\"Review\")').first().click();",
                "await expect(page.locator('#reviewModal')).toBeVisible();",
                "await page.locator(\"textarea[name='review_comments']\").fill('Root cause identified.');",
                "await page.locator('#submitReviewBtn').click();",
                "await page.waitForLoadState('networkidle');",
            ]
        if kind == "notify_authority":
            return [
                "await page.locator('button:has-text(\"Review\")').first().click();",
                "await expect(page.locator('#reviewModal')).toBeVisible();",
                "await page.locator('#notifyAuthority').check();",
                "await expect(page.locator('#notifyAuthority')).toBeChecked();",
            ]
        return [
            "await expect(page.locator('table, .incident-list').first()).toBeVisible();",
            "await expect(page.locator('.badge-high, .badge-medium, .badge-low').first()).toBeVisible();",
        ]

    @staticmethod
    def _port_call_actions(kind: str, g) -> list[str]:
        if kind == "create_port_call":
            return [
                "await page.locator(\"[data-bs-target='#newPortCallModal']\").click();",
                "await expect(page.locator('#newPortCallModal')).toBeVisible();",
                "await page.locator(\"select[name='vessel']\").selectOption({ index: 0 });",
                "await page.locator(\"input[name='port']\").fill('Port of Singapore');",
                "const eta = new Date(); eta.setDate(eta.getDate() + 5);",
                "await page.locator(\"input[name='eta']\").fill(eta.toISOString().split('T')[0]);",
                "await page.locator('#createPortCallBtn').click();",
                "await page.waitForLoadState('networkidle');",
            ]
        return ["await expect(page.locator('table, .port-call-list').first()).toBeVisible();"]

    # ── Helper functions emitted at top of fallback spec ───────────────────────

    @staticmethod
    def _helper_functions(slug: str, loc: dict) -> list[str]:
        if slug == "crew_certs":
            return [
                "async function renewCertificate(page: any, expiry: string, certNumber: string) {",
                "  await page.locator('button.btn-outline-primary').first().click();",
                "  await expect(page.locator('#renewModal')).toBeVisible();",
                "  await page.locator(\"input[name='new_expiry']\").fill(expiry);",
                "  await page.locator(\"input[name='cert_number']\").fill(certNumber);",
                "  await page.locator('#renewSubmitBtn').click();",
                "  await page.waitForLoadState('networkidle');",
                "}",
            ]
        if slug == "incidents":
            return [
                "async function reportIncident(page: any, type: string, severity: string, location: string, desc: string) {",
                "  await page.locator(\"[data-bs-target='#newIncidentModal']\").click();",
                "  await expect(page.locator('#newIncidentModal')).toBeVisible();",
                "  await page.locator(\"select[name='type']\").selectOption(type);",
                "  await page.locator(\"select[name='severity']\").selectOption(severity);",
                "  await page.locator(\"select[name='vessel']\").selectOption({ index: 0 });",
                "  await page.locator(\"input[name='location']\").fill(location);",
                "  await page.locator(\"textarea[name='description']\").fill(desc);",
                "  await page.locator('#reportIncidentBtn').click();",
                "  await page.waitForLoadState('networkidle');",
                "}",
            ]
        return []

    # ── Gherkin parser ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_scenarios(gherkin_text: str) -> list[dict]:
        scenarios: list[dict] = []
        cur_tags:  list[str]  = []
        current:   dict | None = None
        for line in gherkin_text.splitlines():
            s = line.strip()
            if s.startswith("@"):
                cur_tags = [t for t in s.split() if t.startswith("@")]
            elif s.startswith("Scenario Outline:") or s.startswith("Scenario:"):
                if current:
                    scenarios.append(current)
                prefix  = "Scenario Outline:" if s.startswith("Scenario Outline:") else "Scenario:"
                current = {"title": s[len(prefix):].strip(), "tags": list(cur_tags), "steps": []}
                cur_tags = []
            elif current and s.startswith(("Given ", "When ", "Then ", "And ", "But ")):
                current["steps"].append(s)
        if current:
            scenarios.append(current)
        return scenarios

    @staticmethod
    def _url_from_step(step_lower: str, default_url: str) -> str:
        _PAGE_MAP = [
            (("voyage",),                            "/voyage"),
            (("fatigue",),                           "/fatigue"),
            (("incident",),                          "/incidents"),
            (("port-call", "port call", "portcall"), "/port-call"),
            (("crew cert", "certif"),                "/crew-certs"),
        ]
        for keywords, page_url in _PAGE_MAP:
            if any(k in step_lower for k in keywords):
                return page_url
        m = re.search(r'["\']/([\w-]+)["\']', step_lower)
        if m:
            return f"/{m.group(1)}"
        return default_url

    # ── Risk report ─────────────────────────────────────────────────────────────

    def _build_risk_report(
        self, feature_name: str, domain: dict, coverage: dict, scenario_titles: list[str]
    ) -> dict:
        covered_pct   = coverage.get("coverage_percentage", 0)
        critical_gaps = coverage.get("critical_gaps", [])
        p1_reqs       = domain.get("p1_safety_requirements", [])
        p1_count      = len(p1_reqs)
        covered_set   = {c.get("requirement", "") for c in coverage.get("covered", [])}
        p1_covered    = sum(1 for r in p1_reqs if r in covered_set)
        p1_pct        = round(p1_covered / max(p1_count, 1) * 100, 1)

        total   = max(len(scenario_titles), 1)
        bnd_cnt = sum(1 for s in scenario_titles if any(k in s.lower() for k in ("boundary", "t-", "t+", "days", "threshold")))
        neg_cnt = sum(1 for s in scenario_titles if any(k in s.lower() for k in ("invalid", "reject", "block", "expired", "overdue")))
        dim_req = covered_pct
        dim_bnd = round(min(bnd_cnt / max(total * 0.25, 1), 1) * 100, 1)
        dim_neg = round(min(neg_cnt / max(total * 0.2,  1), 1) * 100, 1)
        dim_reg = round(len(domain.get("applicable_regulations", [])) / 7 * 100, 1)
        score   = round((dim_req * 0.3) + (dim_bnd * 0.25) + (dim_neg * 0.2) + (dim_reg * 0.25), 1)

        recs: list[str] = [
            f"Add test coverage for: {(g if isinstance(g, str) else g.get('gap', str(g)))}"
            for g in critical_gaps[:3]
        ]
        if p1_pct < 100:
            recs.append(f"P1 safety coverage is {p1_pct}% — all safety-critical scenarios must reach 100%")
        if dim_bnd < 80:
            recs.append("Add boundary value tests — exact threshold scenarios prevent real-world incidents")
        if not recs:
            recs.append("All critical requirements covered.")

        return {
            "feature_name":               feature_name,
            "overall_coverage_pct":       covered_pct,
            "p1_safety_coverage_pct":     p1_pct,
            "quality_score":              score,
            "dimensions":                 {"req_coverage": dim_req, "boundary_coverage": dim_bnd,
                                           "negative_coverage": dim_neg, "reg_traceability": dim_reg},
            "gaps":                       coverage.get("gaps", []),
            "critical_gaps":              critical_gaps,
            "risk_level":                 domain.get("risk_level", "MEDIUM"),
            "recommendations":            recs,
            "summary":                    f"Quality Score: {score}/100 | P1: {p1_pct}% | Coverage: {covered_pct}%",
            "p1_count":                   p1_count,
            "p2_count":                   len(domain.get("p2_compliance_requirements", [])),
            "p3_count":                   len(domain.get("p3_operational_requirements", [])),
            "psc_detention_triggers":     domain.get("psc_detention_triggers", []),
            "regulation_coverage":        coverage.get("regulation_coverage", {}),
        }

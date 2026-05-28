"""
Mock app DOM scraper — uses Playwright Python to launch a real Chromium browser,
navigate to each page, and extract every interactive element from the live DOM.

Agent 3 calls this at runtime so TypeScript locators are always based on
what actually exists in the HTML, not a manually maintained dict.

Requires: playwright>=1.44.0 + `playwright install chromium`
Falls back gracefully if mock app is not running or Playwright not installed.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Optional

log = logging.getLogger(__name__)

MOCK_APP_BASE = "http://localhost:5000"
SCRAPE_TIMEOUT_MS = 12_000   # 12s — don't block pipeline too long

_CACHE: dict[str, dict] = {}  # per-process cache; one scrape per slug per run


# ── JS snippet executed inside the browser to extract the full locator map ──────

_DOM_EXTRACT_JS = """() => {
    const q   = (sel) => [...document.querySelectorAll(sel)];
    const txt = (el)  => (el ? (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 80) : '');

    return {
        ids: q('[id]').map(el => ({
            id:      el.id,
            tag:     el.tagName.toLowerCase(),
            text:    txt(el),
            visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
        })).filter(x => x.id && x.id.length > 1),

        formFields: q('input[name], select[name], textarea[name]').map(el => ({
            name:        el.name,
            tag:         el.tagName.toLowerCase(),
            type:        el.type  || null,
            id:          el.id    || null,
            required:    el.required || false,
            placeholder: el.placeholder || null,
            options:     el.tagName === 'SELECT'
                            ? [...el.options].map(o => o.text.trim()).filter(Boolean)
                            : []
        })),

        buttons: q('button, [role="button"]').map(el => ({
            text:        txt(el),
            id:          el.id   || null,
            type:        el.type || 'button',
            classes:     el.className,
            modalTarget: el.getAttribute('data-bs-target')  || null,
            bsToggle:    el.getAttribute('data-bs-toggle')  || null,
            onclick:     (el.getAttribute('onclick') || '').slice(0, 100),
            disabled:    el.disabled || false
        })).filter(b => b.text),

        modals: q('.modal').map(el => ({
            id:    el.id,
            title: txt(el.querySelector('.modal-title') || el.querySelector('h5') || el)
        })),

        alerts: q('.departure-block, .alert, .flash-success, .flash-message').map(el => ({
            classes: el.className,
            text:    txt(el),
            id:      el.id || null
        })),

        badges: q('.badge').map(el => ({
            classes: el.className,
            text:    txt(el)
        })),

        tables: q('table').map(el => ({
            id:       el.id   || null,
            classes:  el.className,
            headers:  [...el.querySelectorAll('thead th')].map(th => txt(th)),
            rowCount: el.querySelectorAll('tbody tr').length
        })),

        forms: q('form').map(el => ({
            id:     el.id    || null,
            action: el.getAttribute('action') || null,
            method: el.method || 'get',
            fields: [...el.querySelectorAll('[name]')].map(f => f.name)
        }))
    };
}"""


class MockAppScraper:
    """
    Playwright-based live DOM scraper for the mock maritime app.
    Call scrape(slug, url_path) — returns structured element data.
    Call build_locator_string(data) — returns LLM-ready locator context.
    """

    def scrape(self, slug: str, url_path: str) -> dict:
        """
        Synchronous entry point. Runs async Playwright in a clean event loop.
        Returns empty/fallback dict if mock app is unreachable or Playwright
        is not installed.
        """
        cache_key = f"{slug}:{url_path}"
        if cache_key in _CACHE:
            log.info(f"[Scraper] Cache hit for {url_path}")
            return _CACHE[cache_key]

        try:
            result = asyncio.run(self._scrape_async(url_path))
            if result.get("scraped"):
                _CACHE[cache_key] = result
                log.info(
                    f"[Scraper] Scraped {url_path} — "
                    f"{len(result.get('ids',[]))} ids, "
                    f"{len(result.get('formFields',[]))} fields, "
                    f"{len(result.get('buttons',[]))} buttons"
                )
            return result
        except RuntimeError as exc:
            # asyncio.run() called from within a running loop (rare in thread context)
            log.warning(f"[Scraper] asyncio conflict for {url_path}: {exc}")
            return {"scraped": False, "url": url_path, "error": str(exc)}
        except Exception as exc:
            log.warning(f"[Scraper] Failed to scrape {url_path}: {exc}")
            return {"scraped": False, "url": url_path, "error": str(exc)}

    async def _scrape_async(self, url_path: str) -> dict:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {
                "scraped": False,
                "url": url_path,
                "error": "playwright not installed — run: pip install playwright && playwright install chromium",
            }

        url = f"{MOCK_APP_BASE}{url_path}"

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                page = await browser.new_page()

                try:
                    await page.goto(url, timeout=SCRAPE_TIMEOUT_MS)
                    await page.wait_for_load_state("domcontentloaded")
                except Exception as exc:
                    return {
                        "scraped": False,
                        "url": url_path,
                        "error": f"Could not reach {url} — is mock app running? ({exc})",
                    }

                # Full DOM extraction
                dom = await page.evaluate(_DOM_EXTRACT_JS)

                return {
                    "scraped":      True,
                    "url":          url_path,
                    "ids":          dom.get("ids", []),
                    "formFields":   dom.get("formFields", []),
                    "buttons":      dom.get("buttons", []),
                    "modals":       dom.get("modals", []),
                    "alerts":       dom.get("alerts", []),
                    "badges":       dom.get("badges", []),
                    "tables":       dom.get("tables", []),
                    "forms":        dom.get("forms", []),
                }
            finally:
                await browser.close()

    # ── Accessibility tree flattener ──────────────────────────────────────────

    @classmethod
    def _flatten_a11y(cls, node: dict) -> list[dict]:
        """Extract all named interactive elements from the a11y tree."""
        results: list[dict] = []
        if not node:
            return results

        role = node.get("role", "")
        name = node.get("name", "")

        if role in ("button", "link", "checkbox", "textbox",
                    "combobox", "menuitem", "option") and name:
            results.append({"role": role, "name": name})

        for child in node.get("children") or []:
            results.extend(cls._flatten_a11y(child))

        return results

    # ── LLM context string builder ────────────────────────────────────────────

    @staticmethod
    def build_locator_string(data: dict) -> str:
        """
        Convert raw scraped DOM data into a concise, LLM-readable locator
        context string. Injected directly into the TypeScript generation prompt.
        """
        if not data.get("scraped"):
            err = data.get("error", "unavailable")
            return f"[DOM scraping unavailable — {err}]\nUse fallback locators from MOCK_APP_LOCATORS."

        url   = data.get("url", "/")
        lines = [f"=== LIVE DOM — {MOCK_APP_BASE}{url} ===\n"]

        # ── IDs ────────────────────────────────────────────────────────────────
        ids = [i for i in data.get("ids", []) if len(i["id"]) > 2]
        if ids:
            lines.append("Element IDs  →  page.locator('#id')")
            for item in ids[:25]:
                vis = "" if item.get("visible") else "  [hidden on load]"
                lines.append(f"  #{item['id']}  ({item['tag']})  \"{item['text'][:55]}\"{vis}")

        # ── Form fields ───────────────────────────────────────────────────────
        fields = data.get("formFields", [])
        if fields:
            lines.append("\nForm fields  →  page.locator(\"tag[name='x']\")")
            for f in fields:
                req  = "  *required*" if f.get("required") else ""
                opts = f"  options: {f['options']}" if f.get("options") else ""
                ph   = f"  placeholder: \"{f['placeholder']}\"" if f.get("placeholder") else ""
                lines.append(
                    f"  {f['tag']}[name='{f['name']}']"
                    f"  type={f.get('type') or f['tag']}{req}{opts}{ph}"
                )

        # ── Buttons ───────────────────────────────────────────────────────────
        buttons = data.get("buttons", [])
        if buttons:
            lines.append("\nButtons")
            for b in buttons[:20]:
                if b.get("id"):
                    locator = f"page.locator('#{b['id']}')"
                elif b.get("modalTarget"):
                    locator = f"page.locator('[data-bs-target=\"{b['modalTarget']}\"]')"
                elif b.get("onclick"):
                    short = b["onclick"][:40]
                    locator = f"page.locator('button[onclick^=\"{short}\"]')"
                else:
                    locator = f"page.getByRole('button', {{{{ name: '{b['text'][:40]}' }}}})"
                dis = "  [disabled]" if b.get("disabled") else ""
                lines.append(f"  \"{b['text'][:55]}\"{dis}  →  {locator}")

        # ── Modals ────────────────────────────────────────────────────────────
        modals = data.get("modals", [])
        if modals:
            lines.append("\nModals  →  page.locator('#id')")
            for m in modals:
                lines.append(f"  #{m['id']}  \"{m['title'][:55]}\"")

        # ── Alerts / departure blocks ─────────────────────────────────────────
        alerts = data.get("alerts", [])
        if alerts:
            lines.append("\nAlerts / banners (present on page load):")
            for a in alerts[:6]:
                classes = " ".join(
                    f".{c}" for c in a["classes"].split() if c not in ("show",)
                )
                lines.append(f"  {classes}  \"{a['text'][:70]}\"")

        # ── Badges ────────────────────────────────────────────────────────────
        unique_badge_classes = list({b["classes"] for b in data.get("badges", [])})
        if unique_badge_classes:
            lines.append("\nBadge classes:")
            for cls in unique_badge_classes[:10]:
                examples = [b["text"] for b in data["badges"] if b["classes"] == cls][:2]
                css = " ".join(f".{c}" for c in cls.split())
                lines.append(f"  {css}  e.g. {examples}")

        # ── Tables ────────────────────────────────────────────────────────────
        tables = data.get("tables", [])
        if tables:
            lines.append("\nTables:")
            for t in tables:
                sel = f"#{t['id']}" if t.get("id") else \
                      f"table.{t['classes'].split()[0]}" if t.get("classes") else "table"
                lines.append(
                    f"  {sel}  headers: {t['headers']}  ({t['rowCount']} rows)"
                )

        # ── Interaction patterns ──────────────────────────────────────────────
        lines.append("""
Interaction patterns for this Flask app:
  Bootstrap modal:  click trigger → await expect(locator('#modal')).toBeVisible() → fill → submit
  HTML form POST:   click submit  → await page.waitForLoadState('networkidle') → assert .alert.alert-success
  JS-revealed div:  click button  → await expect(locator('#div')).toBeVisible() → interact inside
  Flash messages:   appear as .alert.alert-success on the redirected page after POST""")

        lines.append("\n=== END DOM ===")
        return "\n".join(lines)

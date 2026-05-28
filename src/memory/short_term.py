"""
Short-term memory: holds the current pipeline session state.
Lives in-memory only — cleared when a new feature is submitted.
"""

from datetime import datetime


class ShortTermMemory:
    def __init__(self):
        self._store: dict = {}
        self._history: list[dict] = []
        self._created_at: str = datetime.utcnow().isoformat()

    # ── Basic key/value store ──────────────────────────────────────────────────

    def set(self, key: str, value) -> None:
        self._store[key] = value
        self._history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action":    "set",
            "key":       key,
            "preview":   str(value)[:120] + "..." if len(str(value)) > 120 else str(value),
        })

    def get(self, key: str, default=None):
        return self._store.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._store

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        self._store.clear()
        self._history.clear()
        self._created_at = datetime.utcnow().isoformat()

    # ── Inspection helpers ─────────────────────────────────────────────────────

    def get_all(self) -> dict:
        return dict(self._store)

    def get_history(self) -> list[dict]:
        return list(self._history)

    def get_session_summary(self) -> dict:
        """Returns a UI-friendly snapshot of current session state."""
        return {
            "session_started":    self._created_at,
            "keys_stored":        list(self._store.keys()),
            "total_operations":   len(self._history),
            "feature_loaded":     self.has("feature_text"),
            "analysis_complete":  self.has("domain_analysis"),
            "gherkin_generated":  self.has("gherkin_output"),
            "scripts_generated":  self.has("playwright_scripts"),
            "report_generated":   self.has("coverage_report"),
        }

    def get_agent_context(self) -> dict:
        """Returns only the keys agents need to pass between themselves."""
        keys = ["feature_text", "feature_name", "domain_analysis",
                "gherkin_output", "playwright_scripts", "coverage_report"]
        return {k: self._store[k] for k in keys if k in self._store}

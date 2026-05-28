"""
Session store — SQLite-backed history for cross-session recall.
Stores full pipeline results indexed by session_id.
Separate from LangGraph's checkpoint store (which handles graph execution state).
"""

from __future__ import annotations
import json, sqlite3, logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parents[2] / "memory" / "sessions.db"


class SessionStore:
    """Persist and query pipeline run results across sessions."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id     TEXT PRIMARY KEY,
                feature_name   TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                risk_level     TEXT,
                scenario_count INTEGER,
                quality_score  REAL,
                p1_coverage    REAL,
                audit_score    REAL,
                result_json    TEXT
            )
        """)
        self._conn.commit()

    def save(self, session_id: str, result: dict) -> None:
        de = result.get("domain_analysis",  result.get("domain_enrichment", {}))
        gr = result.get("gherkin_result",   {})
        pr = result.get("playwright_result",result.get("test_result", {}))
        ar = result.get("audit_result",     {})
        rr = pr.get("risk_report", {}) if isinstance(pr, dict) else {}

        sc = gr.get("scenario_count", 0) or (gr.get("validation", {}) or {}).get("scenario_count", 0)
        qs = (rr or {}).get("quality_score", 0)
        p1 = (rr or {}).get("p1_safety_coverage_pct", 0)
        audit_s = (ar or {}).get("overall_score", 0)

        self._conn.execute(
            """INSERT OR REPLACE INTO sessions
               (session_id, feature_name, created_at, risk_level, scenario_count,
                quality_score, p1_coverage, audit_score, result_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                result.get("feature_name", "unknown"),
                datetime.utcnow().isoformat(),
                (de or {}).get("risk_level", "MEDIUM"),
                sc, qs, p1, audit_s,
                json.dumps(result, default=str),
            ),
        )
        self._conn.commit()
        log.info(f"[SessionStore] Saved session {session_id}")

    def get(self, session_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT result_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def list_sessions(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            """SELECT session_id, feature_name, created_at, risk_level,
                      scenario_count, quality_score, p1_coverage, audit_score
               FROM sessions ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "session_id":     r[0],
                "feature_name":   r[1],
                "created_at":     r[2],
                "risk_level":     r[3],
                "scenario_count": r[4],
                "quality_score":  r[5],
                "p1_coverage":    r[6],
                "audit_score":    r[7],
            }
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()


# Module-level singleton
session_store = SessionStore()

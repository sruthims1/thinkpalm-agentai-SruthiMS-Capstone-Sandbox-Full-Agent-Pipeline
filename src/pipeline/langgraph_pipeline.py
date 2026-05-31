"""
LangGraph Pipeline — 4-agent Maritime QA workflow.

Graph topology:
  START
    └─► maritime_domain      (Agent 1 — risk analysis + domain enrichment)
          └─► test_strategist (Agent 2 — Gherkin BDD generation)
                └─► automation_engineer (Agent 3 — Playwright TypeScript)
                      └─► qa_auditor    (Agent 4 — traceability + audit)
                            └─► END

SQLite checkpointer provides cross-session memory and pipeline resume.
Falls back to MemorySaver if langgraph-checkpoint-sqlite is not installed.
"""

from __future__ import annotations
import uuid, logging
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from agents.maritime_domain_agent     import MaritimeDomainAgent
from agents.test_strategist_agent     import TestStrategistAgent
from agents.automation_engineer_agent import AutomationEngineerAgent
from agents.qa_auditor_agent          import QAAuditorAgent

log = logging.getLogger(__name__)


# ── Shared pipeline state ───────────────────────────────────────────────────────
class MaritimeQAState(TypedDict):
    session_id:          str
    feature_name:        str
    feature_description: str
    domain_analysis:     dict
    gherkin_result:      dict
    playwright_result:   dict
    audit_result:        dict
    logs:                list[str]
    error:               Optional[str]


# ── Graph factory ───────────────────────────────────────────────────────────────
def _build_graph(log_cb=None, checkpointer=None):
    logger = log_cb or (lambda msg: log.info(msg))

    domain_agent = MaritimeDomainAgent(log_callback=logger)
    bdd_agent    = TestStrategistAgent(log_callback=logger)
    ts_agent     = AutomationEngineerAgent(log_callback=logger)
    audit_agent  = QAAuditorAgent(log_callback=logger)

    def maritime_domain_node(state: MaritimeQAState) -> dict:
        logger(f"[Pipeline] Starting Agent 1: Maritime Domain Expert")
        try:
            result = domain_agent.analyze(state["feature_name"], state["feature_description"])
            return {
                "domain_analysis": result,
                "logs": state.get("logs", []) + [
                    f"[Maritime Domain Expert] Complete — risk={result.get('risk_level','?')}, "
                    f"regs={len(result.get('applicable_regulations',[]))}"
                ],
            }
        except Exception as exc:
            logger(f"[maritime_domain_node] ERROR: {exc}")
            return {
                "domain_analysis": {},
                "error": str(exc),
                "logs": state.get("logs", []) + [f"[Maritime Domain Expert] ERROR: {exc}"],
            }

    def test_strategist_node(state: MaritimeQAState) -> dict:
        if state.get("error"):
            return {}
        logger(f"[Pipeline] Starting Agent 2: Test Strategist")
        try:
            result = bdd_agent.generate(
                state["feature_name"],
                state["feature_description"],
                state.get("domain_analysis", {}),
            )
            return {
                "gherkin_result": result,
                "logs": state.get("logs", []) + [
                    f"[Test Strategist] Complete — {result.get('scenario_count', 0)} scenarios"
                ],
            }
        except Exception as exc:
            logger(f"[test_strategist_node] ERROR: {exc}")
            return {
                "gherkin_result": {},
                "error": str(exc),
                "logs": state.get("logs", []) + [f"[Test Strategist] ERROR: {exc}"],
            }

    def automation_engineer_node(state: MaritimeQAState) -> dict:
        if state.get("error"):
            return {}
        logger(f"[Pipeline] Starting Agent 3: Automation Engineer")
        try:
            result = ts_agent.generate(
                state["feature_name"],
                state.get("gherkin_result", {}),
                state.get("domain_analysis", {}),
            )
            return {
                "playwright_result": result,
                "logs": state.get("logs", []) + [
                    f"[Automation Engineer] Complete — spec.ts generated, "
                    f"quality={result.get('risk_report', {}).get('quality_score', 0)}/100"
                ],
            }
        except Exception as exc:
            logger(f"[automation_engineer_node] ERROR: {exc}")
            return {
                "playwright_result": {},
                "error": str(exc),
                "logs": state.get("logs", []) + [f"[Automation Engineer] ERROR: {exc}"],
            }

    def qa_auditor_node(state: MaritimeQAState) -> dict:
        if state.get("error"):
            return {}
        logger(f"[Pipeline] Starting Agent 4: QA Auditor")
        try:
            result = audit_agent.audit(
                state["feature_name"],
                state["feature_description"],
                state.get("domain_analysis", {}),
                state.get("gherkin_result", {}),
                state.get("playwright_result", {}),
            )
            return {
                "audit_result": result,
                "logs": state.get("logs", []) + [
                    f"[QA Auditor] Complete — score={result.get('overall_score', 0)}/100, "
                    f"gaps={len(result.get('coverage_gaps', []))}"
                ],
            }
        except Exception as exc:
            logger(f"[qa_auditor_node] ERROR: {exc}")
            return {
                "audit_result": {},
                "error": str(exc),
                "logs": state.get("logs", []) + [f"[QA Auditor] ERROR: {exc}"],
            }

    g = StateGraph(MaritimeQAState)
    g.add_node("maritime_domain",     maritime_domain_node)
    g.add_node("test_strategist",     test_strategist_node)
    g.add_node("automation_engineer", automation_engineer_node)
    g.add_node("qa_auditor",          qa_auditor_node)

    g.add_edge(START,                "maritime_domain")
    g.add_edge("maritime_domain",    "test_strategist")
    g.add_edge("test_strategist",    "automation_engineer")
    g.add_edge("automation_engineer","qa_auditor")
    g.add_edge("qa_auditor",          END)

    return g.compile(checkpointer=checkpointer)


# ── Checkpointer factory ────────────────────────────────────────────────────────
def _get_checkpointer():
    """Return an in-memory checkpointer (one per pipeline run — no shared SQLite file)."""
    try:
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    except Exception:
        return None


# ── Public API ─────────────────────────────────────────────────────────────────
def run_pipeline_sync(
    feature_name: str,
    feature_description: str,
    session_id: str | None = None,
    log_cb=None,
) -> dict:
    """Run the full 4-agent pipeline synchronously. Returns final state as dict."""
    from memory.short_term import session_memory
    session_memory.clear()
    session_memory.set("feature_name", feature_name)
    session_memory.set("feature_text", feature_description)

    sid         = session_id or str(uuid.uuid4())
    checkpointer = _get_checkpointer()
    graph       = _build_graph(log_cb=log_cb, checkpointer=checkpointer)

    initial: MaritimeQAState = {
        "session_id":          sid,
        "feature_name":        feature_name,
        "feature_description": feature_description,
        "domain_analysis":     {},
        "gherkin_result":      {},
        "playwright_result":   {},
        "audit_result":        {},
        "logs":                [],
        "error":               None,
    }

    config = {"configurable": {"thread_id": sid}}
    try:
        final = graph.invoke(initial, config)
    finally:
        if checkpointer and hasattr(checkpointer, "conn"):
            try:
                checkpointer.conn.close()
            except Exception:
                pass

    return dict(final)


def run_pipeline_stream_sync(
    feature_name: str,
    feature_description: str,
    session_id: str | None = None,
    log_cb=None,
):
    """Generator yielding (node_name, node_output_dict) as each agent completes.
    Used by the FastAPI SSE endpoint for real-time streaming."""
    sid          = session_id or str(uuid.uuid4())
    checkpointer = _get_checkpointer()
    graph        = _build_graph(log_cb=log_cb, checkpointer=checkpointer)

    initial: MaritimeQAState = {
        "session_id":          sid,
        "feature_name":        feature_name,
        "feature_description": feature_description,
        "domain_analysis":     {},
        "gherkin_result":      {},
        "playwright_result":   {},
        "audit_result":        {},
        "logs":                [],
        "error":               None,
    }

    config = {"configurable": {"thread_id": sid}}
    try:
        for event in graph.stream(initial, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                yield node_name, node_output
    finally:
        if checkpointer and hasattr(checkpointer, "conn"):
            try:
                checkpointer.conn.close()
            except Exception:
                pass

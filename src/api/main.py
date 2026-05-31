"""
FastAPI backend — REST + SSE endpoints for the MaritimeTestAI React frontend.
Drives the 4-agent LangGraph pipeline with real-time streaming via SSE.
"""

from dotenv import load_dotenv
load_dotenv()

import json, queue, threading, traceback, logging
import requests
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pipeline.langgraph_pipeline import run_pipeline_stream_sync
from memory.short_term   import session_memory
from memory.long_term    import LongTermMemory
from memory.maritime_kb  import MaritimeKnowledgeBase
from memory.sqlite_memory import session_store
from tools.file_tools    import (list_feature_files, read_feature_file, list_generated_tests,
                                  GHERKIN_DIR, TYPESCRIPT_DIR, COVERAGE_DIR, AUDIT_DIR)

app = FastAPI(title="MaritimeTestAI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_stm        = session_memory
_ltm        = LongTermMemory()
_kb         = MaritimeKnowledgeBase()
_log_queues: dict[str, queue.Queue] = {}


# ── Request / response models ──────────────────────────────────────────────────
class RunPipelineRequest(BaseModel):
    feature_name: str
    feature_text: str
    run_id:       str


# ── Pipeline endpoints ─────────────────────────────────────────────────────────
@app.post("/api/pipeline/run")
def run_pipeline(req: RunPipelineRequest):
    """Start the 4-agent LangGraph pipeline in a background thread."""
    log_q: queue.Queue = queue.Queue()
    _log_queues[req.run_id] = log_q

    def _run() -> None:
        accumulated: dict = {
            "feature_name":      req.feature_name,
            "domain_analysis":   {},
            "gherkin_result":    {},
            "playwright_result": {},
            "audit_result":      {},
        }

        def log_cb(msg: str) -> None:
            log_q.put({"type": "log", "message": msg, "ts": datetime.utcnow().isoformat()})

        # Seed short-term memory with the new run
        _stm.clear()
        _stm.set("feature_name", req.feature_name)
        _stm.set("feature_text", req.feature_text)

        try:
            for node_name, node_output in run_pipeline_stream_sync(
                feature_name=req.feature_name,
                feature_description=req.feature_text,
                session_id=req.run_id,
                log_cb=log_cb,
            ):
                # Merge non-empty node output into accumulated state
                for k, v in node_output.items():
                    if v:
                        accumulated[k] = v

                # Mirror agent outputs into short-term memory
                if node_name == "maritime_domain":
                    _stm.set("domain_analysis", accumulated.get("domain_analysis", {}))
                elif node_name == "test_strategist":
                    _stm.set("gherkin_output", accumulated.get("gherkin_result", {}))
                elif node_name == "automation_engineer":
                    _stm.set("playwright_scripts", accumulated.get("playwright_result", {}))
                elif node_name == "qa_auditor":
                    _stm.set("coverage_report", accumulated.get("audit_result", {}))

                # Emit progress event after each agent node
                partial = _build_response(accumulated, req.feature_name, req.feature_text)
                log_q.put({"type": "progress", "agent": node_name, "partial": partial})

            # Build final result
            result = _build_response(accumulated, req.feature_name, req.feature_text)
            result["success"] = True

            # Persist to memories (non-fatal)
            try:
                da = accumulated.get("domain_analysis", {})
                gr = accumulated.get("gherkin_result", {})
                pr = accumulated.get("playwright_result", {})

                _ltm.store_analysis(req.feature_name, req.feature_text, da)
                if gr:
                    _ltm.store_testcases(req.feature_name, gr.get("gherkin_text", ""), gr.get("scenario_count", 0))
                if pr.get("risk_report"):
                    _ltm.store_report(req.feature_name, pr["risk_report"])

                session_store.save(req.run_id, result)
            except Exception as mem_exc:
                log_cb(f"[Memory] Non-fatal persist error: {mem_exc}")

            log_q.put({"type": "done", "result": result})

        except Exception as exc:
            tb = traceback.format_exc()
            log.error("[Pipeline] UNHANDLED EXCEPTION:\n%s", tb)
            log_q.put({
                "type":   "done",
                "result": {"success": False, "error": str(exc), "traceback": tb, "feature_name": req.feature_name},
            })

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "run_id": req.run_id}


@app.get("/api/pipeline/stream/{run_id}")
def stream_logs(run_id: str):
    """SSE endpoint — streams agent progress and final result to the React UI."""
    if run_id not in _log_queues:
        raise HTTPException(status_code=404, detail="Run ID not found")
    log_q = _log_queues[run_id]

    def event_gen():
        try:
            while True:
                try:
                    item = log_q.get(timeout=120)
                    yield f"data: {json.dumps(item)}\n\n"
                    if item.get("type") == "done":
                        break
                except queue.Empty:
                    yield 'data: {"type":"heartbeat"}\n\n'
        finally:
            _log_queues.pop(run_id, None)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Helper ─────────────────────────────────────────────────────────────────────
def _build_response(state: dict, feature_name: str, feature_text: str) -> dict:
    """Map LangGraph accumulated state → frontend-expected response shape."""
    de = state.get("domain_analysis",   {}) or {}
    gr = state.get("gherkin_result",    {}) or {}
    pr = state.get("playwright_result", {}) or {}
    ar = state.get("audit_result",      {}) or {}

    req_list = [
        ln.strip()[2:]
        for ln in feature_text.splitlines()
        if ln.strip().startswith(("- ", "* ")) and len(ln.strip()) > 4
    ]

    return {
        "feature_name":      feature_name,
        "domain_enrichment": de,
        "requirements":      {
            "requirements":       [{"description": r} for r in req_list],
            "total_requirements": len(req_list),
        },
        "gherkin_result":    gr,
        "test_result":       pr,
        "audit_result":      ar,
        "risk_report":       pr.get("risk_report", ar) or {},
    }


# ── JIRA integration endpoint ─────────────────────────────────────────────────
@app.get("/api/jira/fetch")
def jira_fetch(issue_key: str):
    """Fetch a JIRA Cloud issue and return data ready for pipeline ingestion."""
    from services.jira_service import JiraService
    svc = JiraService()
    try:
        return svc.fetch_issue(issue_key.strip().upper())
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 500
        detail = f"JIRA returned {status}"
        if status == 401:
            detail = "JIRA auth failed — check JIRA_EMAIL and JIRA_API_TOKEN in .env"
        elif status == 403:
            detail = "JIRA permission denied — ensure the API token has read access to this project"
        elif status == 404:
            detail = f"Issue '{issue_key}' not found in JIRA"
        raise HTTPException(status_code=status, detail=detail)
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Cannot reach JIRA — check JIRA_URL in .env")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="JIRA request timed out")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.exception("[JiraFetch] Unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Feature file endpoints ─────────────────────────────────────────────────────
@app.get("/api/features")
def get_features():
    return list_feature_files()

@app.get("/api/features/{filename}")
def get_feature(filename: str):
    return read_feature_file(filename)


# ── Memory endpoints ───────────────────────────────────────────────────────────
@app.get("/api/memory/session")
def get_session_memory():
    return {
        "summary": _stm.get_session_summary(),
        "all_data": _stm.get_all(),
        "history": _stm.get_history()[-20:],
    }

@app.get("/api/memory/longterm")
def get_longterm_memory():
    return {
        "stats":     _ltm.get_stats(),
        "analyses":  _ltm.get_all_analyses(),
        "testcases": _ltm.get_all_testcases(),
        "reports":   _ltm.get_all_reports(),
    }

@app.delete("/api/memory/session")
def clear_session_memory():
    _stm.clear()
    return {"status": "cleared"}

@app.delete("/api/memory/longterm")
def clear_longterm_memory():
    _ltm.clear_all()
    return {"status": "cleared"}


# ── Knowledge base endpoints ───────────────────────────────────────────────────
@app.get("/api/kb/regulations")
def get_regulations():
    return {"regulations": _kb.get_all(), "count": _kb.count()}

@app.get("/api/kb/query")
def query_kb(topic: str, n: int = 5):
    return {"results": _kb.query(topic, n_results=n)}


# ── Generated test endpoints ───────────────────────────────────────────────────
@app.get("/api/tests")
def get_generated_tests():
    return list_generated_tests()

@app.get("/api/tests/report/{feature_name}")
def get_report(feature_name: str):
    safe = feature_name.lower().replace(" ", "_")
    for folder, suffix in [(AUDIT_DIR, "_audit_report"), (COVERAGE_DIR, "_coverage_report")]:
        path = folder / f"{safe}{suffix}.json"
        if path.exists():
            return json.loads(path.read_text())
    raise HTTPException(status_code=404, detail="Report not found")

@app.get("/api/tests/gherkin/{feature_name}")
def get_gherkin(feature_name: str):
    safe = feature_name.lower().replace(" ", "_")
    path = GHERKIN_DIR / f"{safe}.feature"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Feature file not found")
    return {"content": path.read_text(encoding="utf-8"), "filename": path.name}

@app.get("/api/tests/playwright/{feature_name}")
def get_playwright(feature_name: str):
    safe = feature_name.lower().replace(" ", "_")
    path = TYPESCRIPT_DIR / f"{safe}.spec.ts"
    if path.exists():
        return {"content": path.read_text(encoding="utf-8"), "filename": path.name}
    raise HTTPException(status_code=404, detail="Test file not found")


# ── Session history (cross-session SQLite) ─────────────────────────────────────
@app.get("/api/sessions")
def list_sessions():
    return {"sessions": session_store.list_sessions(limit=30)}

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    data = session_store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status":    "ok",
        "version":   "2.0.0 (LangGraph 4-agent pipeline)",
        "kb_count":  _kb.count(),
        "ltm_stats": _ltm.get_stats(),
    }

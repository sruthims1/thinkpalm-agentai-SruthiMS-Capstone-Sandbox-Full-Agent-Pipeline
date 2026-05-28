"""
Long-term memory: persists past pipeline runs using ChromaDB.
Survives server restarts — agents can recall similar past analyses
to avoid redundant work and improve consistency across sessions.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings


DB_PATH = str(Path(__file__).resolve().parents[2] / "memory" / "chroma_db")


class LongTermMemory:
    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=DB_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._analyses  = self._client.get_or_create_collection("analyses")
        self._testcases = self._client.get_or_create_collection("testcases")
        self._reports   = self._client.get_or_create_collection("reports")

    # ── Store ──────────────────────────────────────────────────────────────────

    def store_analysis(self, feature_name: str, feature_text: str, analysis: dict) -> str:
        """Persist a domain analysis result. Returns the entry ID."""
        entry_id = self._make_id(feature_name, feature_text)
        self._analyses.upsert(
            ids=[entry_id],
            documents=[feature_text],
            metadatas=[{
                "feature_name":  feature_name,
                "stored_at":     datetime.utcnow().isoformat(),
                "risk_level":    analysis.get("risk_level", "unknown"),
                "req_count":     len(analysis.get("requirements", [])),
                "analysis_json": json.dumps(analysis)[:2000],
            }],
        )
        return entry_id

    def store_testcases(self, feature_name: str, gherkin: str, scenario_count: int) -> str:
        """Persist generated Gherkin test cases."""
        entry_id = self._make_id(feature_name, gherkin)
        self._testcases.upsert(
            ids=[entry_id],
            documents=[gherkin],
            metadatas=[{
                "feature_name":   feature_name,
                "stored_at":      datetime.utcnow().isoformat(),
                "scenario_count": scenario_count,
            }],
        )
        return entry_id

    def store_report(self, feature_name: str, report: dict) -> str:
        """Persist a coverage gap report."""
        report_text = json.dumps(report)
        entry_id = self._make_id(feature_name, report_text)
        self._reports.upsert(
            ids=[entry_id],
            documents=[report_text],
            metadatas=[{
                "feature_name":    feature_name,
                "stored_at":       datetime.utcnow().isoformat(),
                "coverage_pct":    report.get("coverage_percentage", 0),
                "gaps_count":      len(report.get("gaps", [])),
                "critical_gaps":   len(report.get("critical_gaps", [])),
            }],
        )
        return entry_id

    # ── Search ─────────────────────────────────────────────────────────────────

    def search_similar_analyses(self, query_text: str, n_results: int = 3) -> list[dict]:
        """Find past analyses similar to the current feature description."""
        count = self._analyses.count()
        if count == 0:
            return []
        results = self._analyses.query(
            query_texts=[query_text],
            n_results=min(n_results, count),
        )
        return self._format_results(results, "analyses")

    def search_similar_testcases(self, query_text: str, n_results: int = 3) -> list[dict]:
        """Find past test cases for similar features."""
        count = self._testcases.count()
        if count == 0:
            return []
        results = self._testcases.query(
            query_texts=[query_text],
            n_results=min(n_results, count),
        )
        return self._format_results(results, "testcases")

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def get_all_analyses(self) -> list[dict]:
        if self._analyses.count() == 0:
            return []
        result = self._analyses.get(include=["metadatas", "documents"])
        return [
            {
                "id":           result["ids"][i],
                "feature_name": result["metadatas"][i].get("feature_name"),
                "stored_at":    result["metadatas"][i].get("stored_at"),
                "risk_level":   result["metadatas"][i].get("risk_level"),
                "req_count":    result["metadatas"][i].get("req_count"),
                "preview":      result["documents"][i][:200] + "..."
                                if len(result["documents"][i]) > 200
                                else result["documents"][i],
            }
            for i in range(len(result["ids"]))
        ]

    def get_all_testcases(self) -> list[dict]:
        if self._testcases.count() == 0:
            return []
        result = self._testcases.get(include=["metadatas", "documents"])
        return [
            {
                "id":             result["ids"][i],
                "feature_name":   result["metadatas"][i].get("feature_name"),
                "stored_at":      result["metadatas"][i].get("stored_at"),
                "scenario_count": result["metadatas"][i].get("scenario_count"),
                "preview":        result["documents"][i][:300] + "..."
                                  if len(result["documents"][i]) > 300
                                  else result["documents"][i],
            }
            for i in range(len(result["ids"]))
        ]

    def get_all_reports(self) -> list[dict]:
        if self._reports.count() == 0:
            return []
        result = self._reports.get(include=["metadatas"])
        return [
            {
                "id":            result["ids"][i],
                "feature_name":  result["metadatas"][i].get("feature_name"),
                "stored_at":     result["metadatas"][i].get("stored_at"),
                "coverage_pct":  result["metadatas"][i].get("coverage_pct"),
                "gaps_count":    result["metadatas"][i].get("gaps_count"),
                "critical_gaps": result["metadatas"][i].get("critical_gaps"),
            }
            for i in range(len(result["ids"]))
        ]

    def get_stats(self) -> dict:
        return {
            "total_analyses":  self._analyses.count(),
            "total_testcases": self._testcases.count(),
            "total_reports":   self._reports.count(),
        }

    def clear_all(self) -> None:
        self._client.delete_collection("analyses")
        self._client.delete_collection("testcases")
        self._client.delete_collection("reports")
        self._analyses  = self._client.get_or_create_collection("analyses")
        self._testcases = self._client.get_or_create_collection("testcases")
        self._reports   = self._client.get_or_create_collection("reports")

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _make_id(name: str, content: str) -> str:
        raw = f"{name}::{content[:200]}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _format_results(results: dict, source: str) -> list[dict]:
        ids        = results.get("ids", [[]])[0]
        metadatas  = results.get("metadatas", [[]])[0]
        documents  = results.get("documents", [[]])[0]
        distances  = results.get("distances", [[]])[0]
        return [
            {
                "id":          ids[i],
                "source":      source,
                "metadata":    metadatas[i],
                "preview":     documents[i][:200] + "..." if len(documents[i]) > 200 else documents[i],
                "similarity":  round(1 - distances[i], 3) if distances else None,
            }
            for i in range(len(ids))
        ]

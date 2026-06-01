"""
App Feature Knowledge Base — describes each mock app page's workflows,
testable states, and validation rules in generic terms.

Queried by Agent 1 (MaritimeDomainAgent) so that mandatory_edge_cases
and P1/P2/P3 requirements cover every mock app workflow, not just
regulatory boundaries. Stored in ChromaDB alongside the maritime KB.
"""

import json
from pathlib import Path

import chromadb
from chromadb.config import Settings

DB_PATH = str(Path(__file__).resolve().parents[2] / "memory" / "chroma_db")

APP_FEATURES = [
    {
        "id":      "app-crew-certification",
        "topic":   "crew certification stcw certificate expiry renewal departure block filter status badge modal",
        "feature": "Crew Certification Management",
        "url":     "/crew-certs",
        "workflows": [
            "View cert table with Valid/Expiring Soon/Expired status badges per crew member",
            "Filter table by status (All/Expired/Expiring Soon/Valid) via dropdown",
            "Renew certificate via modal (new_expiry date + cert_number) — clears departure block on success",
        ],
        "testable_states": [
            "Any cert Expired → departure-block banner visible, badge-expired shown",
            "Cert expiring within 30 days → warning banner, badge-expiring shown",
            "All certs valid → no banner, no warning badge",
            "After renewal submitted → success flash, departure-block clears",
        ],
        "validations": [
            "Renewal modal requires both new_expiry (future date) and cert_number",
            "Filter change updates visible rows immediately — no page reload",
        ],
    },
    {
        "id":      "app-voyage-planning",
        "topic":   "voyage planning bunker fuel eca piracy route deviation weather new voyage modal departure block",
        "feature": "Voyage Planning",
        "url":     "/voyage",
        "workflows": [
            "View voyage register — table lists voyages with ECA zone badge count and status column",
            "View voyage details — Details button opens panel showing bunker margin status, ECA compliance, weather deviation alert",
            "Confirm route deviation — confirmDeviationBtn in detail panel logs Master approval; clears departure block",
            "Plan new voyage — modal collects vessel, fuel_type, departure_port, arrival_port, departure_date, speed_kts, bunker_qty, distance_nm; success flash on submit",
        ],
        "testable_states": [
            "High-risk area route (Red Sea/Gulf of Aden) → piracy alert banner on page load, no user action needed",
            "ECA route + non-compliant fuel (VLSFO) → ECA badge shows zone count, non-compliance warning in detail panel",
            "ECA route + compliant fuel (MGO/LNG) → ECA badge shows None, no ECA warning",
            "Bunker margin < 5% on arrival → CRITICAL badge (P1 safety)",
            "Bunker margin 5–15% → WARNING badge",
            "Bunker margin > 15% → ADEQUATE, no warning",
            "Weather deviation unconfirmed → departure-block banner visible",
            "After deviation confirmed → success flash, departure-block cleared",
        ],
        "validations": [
            "Zero or negative bunker_qty → form error, submission rejected",
            "Zero or blank speed_kts → form validation error",
            "All modal fields required before createVoyageBtn enabled",
        ],
    },
    {
        "id":      "app-fatigue-management",
        "topic":   "fatigue rest hours officer violation compliant log rest reassign departure block mlc stcw",
        "feature": "Fatigue Management",
        "url":     "/fatigue",
        "workflows": [
            "View officer fatigue list — each officer shows Violation or Compliant badge",
            "Log rest hours — select officer, enter rest_start and rest_end datetimes, submit",
            "Reassign officer — available only for officers with Violation status",
        ],
        "testable_states": [
            "Officer with < 10h rest in 24h → Violation badge, departure-block banner",
            "Officer with < 77h rest in 7-day period → Violation badge, departure-block",
            "All officers compliant → Compliant badges only, no departure-block",
            "After logging adequate rest → status badge updates",
        ],
        "validations": [
            "rest_end must be after rest_start",
            "Officer must be selected before submitting rest log",
        ],
    },
    {
        "id":      "app-incident-reporting",
        "topic":   "incident reporting ism near miss severity high medium low review notify authority departure block overdue",
        "feature": "Incident Reporting",
        "url":     "/incidents",
        "workflows": [
            "View incident list — severity badge, status, and review deadline per incident",
            "Report new incident — modal with type, severity, vessel, location, description",
            "Review incident — review modal with comments field and Notify Authority checkbox",
            "Departure block — appears when High severity incident review is overdue (>24h)",
        ],
        "testable_states": [
            "High severity incident unreviewed and overdue → departure-block banner",
            "All incidents reviewed → no departure-block",
            "Notify Authority checked → notification confirmation shown",
        ],
        "validations": [
            "All fields (type, severity, vessel, location, description) required to report",
            "Review comments required before submitting review",
        ],
    },
    {
        "id":      "app-port-call",
        "topic":   "port call fal pre-arrival notice eta vessel create submit notice status pending",
        "feature": "Port Call Management",
        "url":     "/port-call",
        "workflows": [
            "View port call list — shows vessel, port, ETA, and notice status",
            "Create port call — modal with vessel, port, eta fields",
            "Submit pre-arrival notice — button per port call; updates status to Notice Submitted",
        ],
        "testable_states": [
            "Port call created → appears in list with Pending Notice status",
            "Notice submitted → status updates, no further action required",
        ],
        "validations": [
            "ETA must be a future date",
            "All fields (vessel, port, eta) required",
        ],
    },
]


class AppFeaturesKB:
    """Knowledge base describing the mock app's pages, workflows, and testable states."""

    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=DB_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection("app_features")
        self._seed()

    def _seed(self) -> None:
        ids, docs, metas = [], [], []
        for f in APP_FEATURES:
            ids.append(f["id"])
            docs.append(f"{f['topic']} {f['feature']}")
            metas.append({
                "feature":         f["feature"],
                "url":             f["url"],
                "workflows":       json.dumps(f["workflows"]),
                "testable_states": json.dumps(f["testable_states"]),
                "validations":     json.dumps(f["validations"]),
            })
        self._col.upsert(ids=ids, documents=docs, metadatas=metas)

    def query(self, feature_name: str) -> dict | None:
        """Return the best-matching app feature entry for the given feature name."""
        if self._col.count() == 0:
            return None
        res = self._col.query(query_texts=[feature_name], n_results=1)
        if not res["ids"][0]:
            return None
        meta = res["metadatas"][0][0]
        return {
            "feature":         meta["feature"],
            "url":             meta["url"],
            "workflows":       json.loads(meta["workflows"]),
            "testable_states": json.loads(meta["testable_states"]),
            "validations":     json.loads(meta["validations"]),
        }

    def count(self) -> int:
        return self._col.count()

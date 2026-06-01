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
            "View cert table: navigate to /crew-certs, assert #certTable is visible with tbody rows",
            "Filter by status: select option from #statusFilter (All/expired/expiring_soon/valid), assert table rows update",
            "Renew certificate: click Renew button → #renewModal visible → fill input[name='new_expiry'] and input[name='cert_number'] → click #renewSubmitBtn → assert .alert.alert-success",
            "Departure block cleared: assert #departure-block-{n} not visible after renewal",
        ],
        "testable_states": [
            "Expired cert present → #departure-block-{n} banner visible with text 'VESSEL DEPARTURE BLOCKED'",
            "Expiring cert → #expiry-warning-{n} visible with days countdown in #days-{n}",
            "All certs valid → no #departure-block-{n} elements visible",
            "After renewal → .alert.alert-success flash visible, #departure-block-{n} gone",
        ],
        "validations": [
            "input[name='new_expiry'] and input[name='cert_number'] both required in #renewModal",
            "#statusFilter change filters #certTable rows without page reload",
        ],
    },
    {
        "id":      "app-voyage-planning",
        "topic":   "voyage planning bunker fuel eca piracy route deviation weather new voyage modal departure block",
        "feature": "Voyage Planning",
        "url":     "/voyage",
        "workflows": [
            "View voyage register: navigate to /voyage, assert .card-body table (voyage table) is visible with voyage rows",
            "View voyage details: click button[onclick^='showVoyageDetails'] → assert #voyageDetailCard visible, #weather-deviation-alert visible",
            "Confirm route deviation: inside #voyageDetailCard click #confirmDeviationBtn → assert .alert.alert-success flash",
            "Plan new voyage: click [data-bs-target='#newVoyageModal'] → #newVoyageModal visible → fill select[name='vessel'], select[name='fuel_type'], input[name='departure_port'], input[name='arrival_port'], input[name='departure_date'], input[name='speed_kts'], input[name='bunker_qty'], input[name='distance_nm'] → click #createVoyageBtn → assert .alert.alert-success",
        ],
        "testable_states": [
            "High-risk route → #piracy-alert-VOY-2026-046 visible on page load without user action",
            "ECA zones → .badge.bg-warning.text-dark shows count (e.g. '2') in voyage table row",
            "No ECA zones → .badge.bg-success shows 'None' in voyage table row",
            "Weather deviation pending → #weather-deviation-alert visible inside #voyageDetailCard",
            "After deviation confirmed → .alert.alert-success visible, #weather-deviation-alert gone",
        ],
        "validations": [
            "All fields in #newVoyageModal required before #createVoyageBtn submits",
            "input[name='bunker_qty'] and input[name='speed_kts'] must be positive numbers",
        ],
    },
    {
        "id":      "app-fatigue-management",
        "topic":   "fatigue rest hours officer violation compliant log rest reassign departure block mlc stcw",
        "feature": "Fatigue Management",
        "url":     "/fatigue",
        "workflows": [
            "View officer list: navigate to /fatigue, assert #fatigue-violation-{n} badges visible for officers in violation",
            "Log rest hours: select from select[name='officer_id'], fill input[name='rest_start'] and input[name='rest_end'], click #logRestBtn → assert .alert.alert-success",
            "Reassign officer: click 'Reassign Watch' button for officer in violation → assert page reloads with updated status",
        ],
        "testable_states": [
            "Officer violation → #fatigue-violation-{n} element visible, .departure-block banner visible",
            "All compliant → no #fatigue-violation-{n} elements, no .departure-block banner",
            "After logging rest → .alert.alert-success flash, violation badge may clear",
        ],
        "validations": [
            "input[name='rest_end'] must be after input[name='rest_start']",
            "select[name='officer_id'] must be selected before #logRestBtn submits",
        ],
    },
    {
        "id":      "app-incident-reporting",
        "topic":   "incident reporting ism near miss severity high medium low review notify authority departure block overdue",
        "feature": "Incident Reporting",
        "url":     "/incidents",
        "workflows": [
            "View incidents: navigate to /incidents, assert incident list visible with #overdue-incident-{id} for overdue items",
            "Report incident: click [data-bs-target='#newIncidentModal'] → #newIncidentModal visible → fill select[name='type'], select[name='severity'], select[name='vessel'], input[name='location'], textarea[name='description'] → click #reportIncidentBtn → assert .alert.alert-success",
            "Review incident: click Review button → #reviewModal visible → fill textarea[name='root_cause'] → optionally check #notifyAuthority → click #submitReviewBtn → assert .alert.alert-success",
        ],
        "testable_states": [
            "Overdue high-severity incident → #overdue-incident-INC-2026-001 visible, .departure-block banner visible",
            "All reviewed → no .departure-block banner",
            "#notifyAuthority checked → #auth-notify-{id} shows notification confirmed",
        ],
        "validations": [
            "textarea[name='root_cause'] required in #reviewModal before #submitReviewBtn works",
            "All fields (type, severity, vessel, location, description) required in #newIncidentModal",
        ],
    },
    {
        "id":      "app-port-call",
        "topic":   "port call fal pre-arrival notice eta vessel create submit notice status pending customs dangerous goods",
        "feature": "Port Call Management",
        "url":     "/port-call",
        "workflows": [
            "View port calls: navigate to /port-call, assert port call rows visible with #notice-24h-{n} alerts for pending notices",
            "View details: click Details button → #portCallDetails panel visible showing #fal1-status, #fal5-status, #dg-status",
            "Submit notice: click #submitNoticeBtn inside #noticeForm → assert .alert.alert-success",
            "Create port call: click [data-bs-target='#newPortCallModal'] → #newPortCallModal visible → fill select[name='vessel'], input[name='port'], input[name='eta'], input[name='etd'], input[name='agent'] → click #createPortCallBtn → assert .alert.alert-success",
        ],
        "testable_states": [
            "Notice pending → #notice-24h-{n} alert visible in port call row",
            "FAL Form 1 not submitted → #fal1-status shows 'Not Submitted' in #portCallDetails",
            "Dangerous goods declared → #dg-status shows DG info in #portCallDetails",
            "After notice submitted → .alert.alert-success, #notice-24h-{n} clears",
        ],
        "validations": [
            "input[name='eta'] must be a future date; input[name='etd'] must be after eta",
            "All fields (vessel, port, eta, etd, agent) required in #newPortCallModal",
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

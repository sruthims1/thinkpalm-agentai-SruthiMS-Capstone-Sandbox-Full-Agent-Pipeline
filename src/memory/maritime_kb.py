"""
Maritime Regulation Knowledge Base.
Pre-populated with real IMO regulation text, STCW certificate requirements,
MLC rest hour rules, PSC deficiency patterns, and VLCC voyage planning rules.
Agents query this KB to enrich their analysis with authoritative domain knowledge.
"""

import json
from pathlib import Path
import chromadb
from chromadb.config import Settings

DB_PATH = str(Path(__file__).resolve().parents[2] / "memory" / "chroma_db")

REGULATIONS = [
    # ── STCW Certificates ─────────────────────────────────────────────────────
    {
        "id": "stcw-i-2-coc",
        "topic": "stcw certificate of competency validity renewal master officer",
        "regulation": "STCW Regulation I/2",
        "clause": "Paragraph 3.1",
        "text": (
            "Every certificate issued under STCW shall be kept valid by revalidation at intervals "
            "not exceeding 5 years. A seafarer must provide evidence of: (a) approved assessment; or "
            "(b) approved seagoing service of not less than 1 year in an appropriate capacity during "
            "the preceding 5 years. Expired CoC = vessel unseaworthy, departure must be blocked."
        ),
        "certificate_type": "Certificate of Competency (CoC)",
        "validity_years": 5,
        "test_implications": [
            "CoC expires every 5 years — boundary tests at T-30, T-7, T-0 days",
            "Revalidation requires seagoing service evidence — test incomplete renewal rejection",
            "Expired CoC must block departure and prevent watch assignment",
            "Exactly T-30 days = Expiring Soon (not Valid)",
            "Exactly T-0 days = Expired (not Expiring Soon)",
        ],
        "psc_risk": "HIGH — Code 2 deficiency, common detention cause",
    },
    {
        "id": "stcw-basic-safety",
        "topic": "stcw basic safety training bst certificate refresher validity",
        "regulation": "STCW Regulation VI/1",
        "clause": "Manila Amendment 2010, Section A-VI/1",
        "text": (
            "Basic Safety Training certificates must be revalidated every 5 years. "
            "Lapsed certificates (past expiry) require full refresher training — NOT just revalidation. "
            "Seafarers must not be assigned shipboard duties without valid BST."
        ),
        "certificate_type": "STCW Basic Safety Training",
        "validity_years": 5,
        "test_implications": [
            "Lapsed BST requires full refresher, not revalidation — test different renewal path",
            "Must not assign duties without valid BST",
            "Boundary: T-30 warning, T-7 critical, T-0 expired + departure block",
        ],
        "psc_risk": "HIGH — Code 2 deficiency",
    },
    {
        "id": "stcw-medical-fitness",
        "topic": "stcw medical fitness certificate validity under 18 mid voyage expiry",
        "regulation": "STCW Regulation I/2 + MLC Standard A1.2",
        "clause": "MLC Standard A1.2, Paragraph 7",
        "text": (
            "Medical fitness certificates are valid for 2 years (1 year if under 18). "
            "Seafarer with expired medical cert must not be assigned duties on board. "
            "EXCEPTION: if certificate expires in the course of a voyage, it remains valid until "
            "the next port where a medical practitioner is available — but the seafarer must be "
            "assessed as soon as possible. This exception does NOT apply at time of departure."
        ),
        "certificate_type": "Medical Fitness Certificate",
        "validity_years": 2,
        "test_implications": [
            "Medical cert validity = 2 years (shorter than CoC 5 years) — generate separate boundary tests",
            "Under-18 seafarers: 1-year validity — test age-based expiry rule",
            "Mid-voyage expiry: valid until next port — but cannot DEPART with expired cert",
            "Exception does not apply at departure — test departure block still applies",
            "At least 1 valid medical cert per vessel mandatory at all times",
        ],
        "psc_risk": "HIGH — MLC violation, Code 15 deficiency",
    },
    {
        "id": "stcw-gmdss",
        "topic": "gmdss radio operator certificate validity watch communication emergency",
        "regulation": "STCW Regulation IV/2",
        "clause": "Section A-IV/2, Table A-IV/2",
        "text": (
            "At least one officer on EACH NAVIGATIONAL WATCH must hold a valid GMDSS General Operator "
            "Certificate. GMDSS certs are valid for 5 years. If the only GMDSS-certified officer has "
            "an expired cert, the vessel cannot maintain a legal watch and departure must be blocked. "
            "GMDSS proficiency check required at revalidation."
        ),
        "certificate_type": "GMDSS General Operator Certificate",
        "validity_years": 5,
        "test_implications": [
            "Each watch must have one valid GMDSS officer — test per-watch coverage",
            "Single GMDSS officer expired = departure block for entire vessel",
            "GMDSS revalidation requires proficiency check — test incomplete renewal",
        ],
        "psc_risk": "CRITICAL — No GMDSS = vessel cannot maintain distress watch",
    },
    # ── MLC 2006 Fatigue ──────────────────────────────────────────────────────
    {
        "id": "mlc-rest-hours-core",
        "topic": "mlc rest hours minimum 10 hours 24h 77 hours 7 days watchkeeping fatigue",
        "regulation": "MLC 2006 Regulation 2.3",
        "clause": "Standard A2.3, Paragraphs 5-6",
        "text": (
            "Minimum hours of rest: NOT LESS THAN 10 hours in any 24-hour period; "
            "NOT LESS THAN 77 hours in any seven-day period. "
            "Rest may be divided into NO MORE THAN TWO periods, one of which shall be "
            "AT LEAST SIX HOURS. Interval between consecutive rest periods shall NOT EXCEED 14 hours."
        ),
        "validity_years": None,
        "test_implications": [
            "9h 59m rest in 24h = VIOLATION (not 10h minimum)",
            "Exactly 10h rest in 24h = COMPLIANT (boundary)",
            "76h 59m in 7 days = VIOLATION",
            "Exactly 77h in 7 days = COMPLIANT (boundary)",
            "Rest split 5h + 5h = VIOLATION (no period ≥ 6h)",
            "Rest split 6h + 4h = COMPLIANT (one period = 6h exactly)",
            "Gap between rest periods > 14h = VIOLATION even if total rest is adequate",
            "Three rest periods in 24h = VIOLATION (max 2 periods allowed)",
        ],
        "psc_risk": "HIGH — Code 15 MLC deficiency, 11.3% of all PSC deficiencies",
    },
    {
        "id": "mlc-rest-midnight",
        "topic": "mlc rest hours midnight boundary spanning period calculation",
        "regulation": "MLC 2006 Regulation 2.3",
        "clause": "Standard A2.3, Paragraph 10 + ILO Guidelines",
        "text": (
            "A rest period spanning midnight is counted as ONE continuous period for compliance purposes. "
            "22:00-08:00 = 10 hours continuous rest = COMPLIANT. "
            "The system must NOT split midnight-spanning periods into two separate calendar-day periods "
            "when checking compliance. Records must show the full continuous period."
        ),
        "validity_years": None,
        "test_implications": [
            "Rest 22:00-08:00 (10h spans midnight) = 1 period = compliant — must NOT be split",
            "Rest 23:30-09:30 (10h) = compliant despite spanning midnight",
            "System must calculate total duration, not calendar-day segments",
        ],
        "psc_risk": "HIGH — Incorrect midnight calculation = false compliance records",
    },
    {
        "id": "mlc-emergency-override",
        "topic": "mlc rest hours emergency override distress master authorisation compensatory",
        "regulation": "MLC 2006 Regulation 2.3",
        "clause": "Standard A2.3, Paragraph 14",
        "text": (
            "Master may suspend rest schedules during genuine emergency situations (distress, safety of ship). "
            "REQUIREMENTS: (1) Master's written authorisation required. (2) Override must be logged with "
            "reason, duration, and officer name. (3) Compensatory rest must be provided ASAP after emergency. "
            "Override does NOT reset the 7-day running total."
        ),
        "validity_years": None,
        "test_implications": [
            "Emergency override without Master authorisation = system must reject",
            "Override must be logged — test audit trail created",
            "Compensatory rest workflow must be triggered after override",
            "7-day total continues accumulating during override period",
        ],
        "psc_risk": "MEDIUM — Override without documentation = ISM non-conformance",
    },
    # ── ISM Code Incidents ─────────────────────────────────────────────────────
    {
        "id": "ism-incident-reporting",
        "topic": "ism incident reporting accident near miss 24 hours flag state authority",
        "regulation": "ISM Code Section 9",
        "clause": "Section 9.1 — Reports and Analysis",
        "text": (
            "Non-conformities, accidents and hazardous situations (near misses) MUST be reported "
            "to the Company and investigated. Preliminary report of a serious accident: submitted "
            "to flag State Administration WITHIN 24 HOURS. Near-miss reports cannot be deleted — "
            "they form part of the ISM audit trail. Root cause analysis required before closure. "
            "Corrective action must be documented and tracked to completion."
        ),
        "validity_years": None,
        "test_implications": [
            "24h deadline for authority notification — test overdue escalation at T+24h+1min",
            "High severity = serious accident = 24h flag state notification mandatory",
            "Near miss cannot be deleted — test delete attempt is rejected",
            "Root cause required before status = Approved — test blank root cause rejection",
            "Corrective action must be logged — test closure without corrective action rejected",
        ],
        "psc_risk": "CRITICAL — ISM non-conformance, vessels detained for missing corrective actions",
    },
    # ── FAL Convention Port Call ───────────────────────────────────────────────
    {
        "id": "fal-pre-arrival",
        "topic": "fal pre-arrival notification 24h 96h port clearance dangerous goods eu",
        "regulation": "FAL Convention + EU Directive 2002/59/EC",
        "clause": "FAL.3/Circ.194, EU Directive Article 4",
        "text": (
            "24-hour pre-arrival notice: mandatory for all EU ports. "
            "For voyages < 24 hours: notice submitted at time of departure from previous port. "
            "Dangerous goods on board: 24h notice mandatory regardless of voyage duration. "
            "96-hour notice: required for VLCC and passenger vessels at specific ports. "
            "FAL Form 1 (General Declaration) required for ALL vessel arrivals. "
            "FAL Form 5 (Crew List) required for ALL vessel arrivals. "
            "Missing pre-arrival notice = port authority may DENY entry."
        ),
        "validity_years": None,
        "test_implications": [
            "24h notice pending when ETA < 24h away = critical alert",
            "Voyage < 24h: notice must be submitted at departure — test timing rule",
            "Dangerous goods + no 24h notice = port entry denial scenario",
            "FAL Form 1 missing = port call cannot proceed to In Port status",
            "Submit 24h notice before 96h notice = workflow warning",
            "ETD before ETA = validation error",
        ],
        "psc_risk": "HIGH — Port denial, demurrage costs for missed notifications",
    },
    # ── MARPOL ECA ────────────────────────────────────────────────────────────
    {
        "id": "marpol-eca-sulphur",
        "topic": "marpol eca sulphur fuel switch vlsfo mgo north sea english channel",
        "regulation": "MARPOL Annex VI Regulation 14",
        "clause": "Regulation 14.1 and 14.4",
        "text": (
            "Sulphur limits: 0.10% inside ECAs; 0.50% globally (from Jan 2020). "
            "ECAs: North Sea (SOx), Baltic Sea (SOx), English Channel, North American ECA, US Caribbean ECA. "
            "Fuel switch to MGO (0.1%) required AT LEAST 1 HOUR before ECA entry. "
            "VLSFO (0.5%) is NOT compliant inside ECA — will result in deficiency. "
            "Vessels fitted with approved exhaust gas cleaning systems (scrubbers) may use HFO inside ECA."
        ),
        "validity_years": None,
        "test_implications": [
            "Route through North Sea/English Channel + VLSFO = ECA compliance WARNING",
            "Route through ECA + MGO = compliant, no warning",
            "Route with no ECA zones = no compliance warning regardless of fuel type",
            "Fuel switch reminder must trigger 1h before ECA entry",
            "VLSFO + scrubber = compliant in ECA — test scrubber exception",
        ],
        "psc_risk": "HIGH — MARPOL violation, flag state prosecution, port detention",
    },
    # ── SOLAS Voyage Planning ─────────────────────────────────────────────────
    {
        "id": "solas-passage-planning",
        "topic": "solas passage planning voyage waypoints appraisal execution monitoring route",
        "regulation": "SOLAS Chapter V, Regulation 34",
        "clause": "Regulation 34.1-34.2 + IMO Resolution A.893(21)",
        "text": (
            "All ships shall carry out voyage/passage planning prior to proceeding to sea. "
            "The voyage plan must cover the ENTIRE voyage from berth to berth. "
            "Four stages: (1) APPRAISAL — gather info, charts, weather, hazards; "
            "(2) PLANNING — lay off route, identify dangers, contingencies; "
            "(3) EXECUTION — monitor progress, verify position at waypoints; "
            "(4) MONITORING — continuous position checking, deviation alerts. "
            "Weather routing deviations must be documented and approved by Master."
        ),
        "validity_years": None,
        "test_implications": [
            "Voyage without waypoints = incomplete passage plan = SOLAS violation",
            "Weather deviation must be confirmed by Master — test unauthorised deviation rejection",
            "Voyage plan must cover departure berth to arrival berth — test partial plans rejected",
            "Route deviation must update ETA and be logged",
        ],
        "psc_risk": "HIGH — Code 10 (Safety of Navigation) deficiency",
    },
    {
        "id": "solas-bunker-sufficiency",
        "topic": "bunker fuel planning sufficiency margin voyage adequacy critical warning",
        "regulation": "SOLAS Chapter II-1, Regulation 26 + INTERTANKO Guidelines",
        "clause": "Regulation 26.3 + INTERTANKO Bunker Sufficiency Guidelines",
        "text": (
            "Every ship shall carry sufficient fuel for the intended voyage. "
            "Industry minimum standards (INTERTANKO/BIMCO): "
            "ADEQUATE: bunker margin > 15% of estimated consumption on arrival. "
            "WARNING: bunker margin 5-15% on arrival — remedial action recommended. "
            "CRITICAL: bunker margin < 5% on arrival — propulsion failure risk, safety-critical. "
            "Zero bunker entry is invalid — must be rejected by the system."
        ),
        "validity_years": None,
        "test_implications": [
            "0 MT bunker = validation error — must reject",
            "Negative bunker = validation error — must reject",
            "Margin < 5% = CRITICAL flag (safety-critical, P1)",
            "Margin 5-15% = WARNING (P2 compliance)",
            "Margin > 15% = ADEQUATE (green, no warning)",
            "Boundary: exactly 15% = ADEQUATE (not Warning)",
            "Weather deviation adds consumption — test revised margin recalculation",
        ],
        "psc_risk": "CRITICAL — Propulsion failure at sea = distress situation",
    },
    # ── PSC Deficiency Intelligence ────────────────────────────────────────────
    {
        "id": "psc-top-deficiencies",
        "topic": "psc port state control inspection deficiency detention common cause",
        "regulation": "Paris MOU / Tokyo MOU Annual Reports 2021-2023",
        "clause": "Paris MOU 2023 Annual Report — Top Deficiency Codes",
        "text": (
            "Top PSC detention causes (Paris MOU 2023): "
            "1. Certificates & Documentation (Code 2): 14.7% — expired CoC, Medical, GMDSS. "
            "2. Fire Safety Systems (Code 4): 18.2% — most frequent deficiency overall. "
            "3. Working/Living Conditions (Code 15): 11.3% — MLC rest hour violations, pay records. "
            "4. Lifesaving Appliances (Code 7): 9.8% — lifeboat, EPIRB, immersion suits. "
            "5. Safety of Navigation (Code 10): 8.1% — ECDIS, charts, passage plan. "
            "High-risk flags (target factor > 1.5): Marshall Islands, Palau, Comoros, Tuvalu. "
            "Any vessel with 3+ deficiencies in last 3 inspections = concentrated inspection."
        ),
        "validity_years": None,
        "test_implications": [
            "Expired certs = most common detention cause — ALL cert types need thorough tests",
            "Missing rest hour records = Code 15 detention — rest logging completeness must be tested",
            "ISM non-conformance without corrective action = detention trigger",
            "3+ past deficiencies = concentrated inspection flag — test PSC risk escalation",
        ],
        "psc_risk": "REFERENCE DATA — Used to prioritise P1/P2 test classification",
    },
    # ── Piracy / Security ─────────────────────────────────────────────────────
    {
        "id": "bmp5-piracy-hra",
        "topic": "piracy high risk area hra bmp5 best management practices indian ocean gulf aden",
        "regulation": "IMO MSC-FAL.1/Circ.3 + BMP5",
        "clause": "BMP5 Section 2 — High Risk Area Definition",
        "text": (
            "High Risk Area (HRA) for piracy: Red Sea, Gulf of Aden, Somali Basin, Arabian Sea, "
            "Indian Ocean (bounded: N lat 26N, S lat 10S, W long 45E, E long 78E). "
            "BMP5 requirements before entering HRA: (1) Register with MSCHOA; "
            "(2) Report to UKMTO; (3) Complete vessel hardening measures; "
            "(4) Conduct pre-transit briefing with crew. "
            "Masters must report piracy/suspicious activity to IMB Piracy Reporting Centre (Kuala Lumpur). "
            "Malacca Strait: monitored by ReCAAP — separate reporting requirement."
        ),
        "validity_years": None,
        "test_implications": [
            "Voyage through Red Sea/Gulf of Aden = P1 piracy alert mandatory",
            "Voyage through Malacca Strait = piracy watch (ReCAAP monitored)",
            "Piracy alert must appear on page load WITHOUT user action",
            "Alert must show vessel name + IMB notification confirmation",
            "BMP5 pre-transit checklist must be completable before HRA entry",
            "No piracy alert for Pacific/Atlantic routes — test false positive absence",
        ],
        "psc_risk": "CRITICAL — Failure to follow BMP5 = vessel and crew safety at risk",
    },
    # ── STCW Certificate Type Catalogue ───────────────────────────────────────
    {
        "id": "stcw-cert-type-catalogue",
        "topic": "stcw certificate types validity periods renewal coc bst medical gmdss pscrb advanced fire fighting watchkeeping endorsement",
        "regulation": "STCW Convention Annex — Regulations I/2, II/1, III/1, IV/2, VI/1, VI/2, VI/3, VI/4",
        "clause": "Manila Amendments 2010 — Certificate Validity Table",
        "text": (
            "STCW certificate validity periods (all require renewal every 5 years unless stated): "
            "Certificate of Competency (CoC) — Master, Chief Mate, OOW Deck: 5 years. "
            "Certificate of Competency — Chief Engineer, Second Engineer, OOW Engine: 5 years. "
            "GMDSS General Operator Certificate (GOC): 5 years. "
            "STCW Basic Safety Training (BST — STCW VI/1): 5 years. "
            "Proficiency in Survival Craft and Rescue Boats (PSCRB — STCW VI/2): 5 years. "
            "Advanced Fire Fighting (AFF — STCW VI/3): 5 years. "
            "Medical First Aid / Medical Care (STCW VI/4): 5 years. "
            "Medical Fitness Certificate (MLC Standard A1.2): 2 years (1 year if seafarer is under 18). "
            "Flag State Endorsement (recognising foreign CoC): must match CoC expiry date — expiry of endorsement = cannot serve in endorsed rank even if underlying CoC is valid. "
            "Each certificate type has INDEPENDENT expiry — a seafarer can have a valid CoC but an expired PSCRB or Flag State Endorsement, which independently triggers departure block."
        ),
        "validity_years": 5,
        "test_implications": [
            "CoC valid but PSCRB expired = departure block — test each cert type independently",
            "Flag State Endorsement expires before CoC = departure block — test endorsement-only expiry scenario",
            "Medical cert: 2-year validity (not 5) — boundary at T-30, T-0 from 2-year date",
            "Under-18 seafarer: medical cert valid 1 year only — test age-based threshold",
            "All 7 cert types can expire independently — test mixed status: some valid, one expired",
            "Renewing CoC does NOT automatically renew PSCRB or AFF — test partial renewal",
            "Boundary: any single cert type expiring within 30 days = Expiring Soon badge + warning banner",
            "Boundary: any single cert type expired = Expired badge + departure block — even if all others valid",
        ],
        "psc_risk": "HIGH — Code 2 deficiency covers all certificate types; expired PSCRB or AFF is common PSC finding",
    },
    # ── STCW Hours of Work ─────────────────────────────────────────────────────
    {
        "id": "stcw-hours-of-work",
        "topic": "stcw hours of work maximum 14 hours 24h 72 hours 7 days watchkeeping fatigue work limit",
        "regulation": "STCW Convention Regulation VIII/1 + Section A-VIII/1",
        "clause": "STCW Code Section A-VIII/1, Paragraphs 1-2",
        "text": (
            "STCW A-VIII/1 sets MAXIMUM hours of WORK (complementary to MLC minimum rest): "
            "Maximum hours of work: NOT MORE THAN 14 hours in any 24-hour period; "
            "NOT MORE THAN 72 hours in any seven-day period. "
            "MLC 2006 sets MINIMUM REST: at least 10 hours in 24h, at least 77 hours in 7 days. "
            "BOTH standards apply simultaneously — a seafarer must comply with BOTH the work maximum AND the rest minimum. "
            "It is possible to violate STCW work limits while technically meeting MLC rest minimums: "
            "Example: 14h work + 10h rest in 24h = MLC compliant (10h rest met) but STCW violation (14h work is boundary, 14h+1min = violation). "
            "The stricter of the two standards always applies. Watchkeeping officers are subject to both."
        ),
        "validity_years": None,
        "test_implications": [
            "14h 00m work in 24h = STCW compliant (boundary — exactly at limit)",
            "14h 01m work in 24h = STCW VIOLATION — must trigger violation badge",
            "72h 00m work in 7 days = STCW compliant (boundary)",
            "72h 01m work in 7 days = STCW VIOLATION",
            "10h rest in 24h = MLC compliant BUT check if work hours also within 14h limit",
            "Seafarer working 14h 30m + resting 9h 30m = STCW violation (work) AND MLC violation (rest) — test compound violation",
            "Officer reassigned after STCW violation — test reassign button available only for violation status",
            "Violation badge must specify whether STCW work-hours or MLC rest-hours violation (or both)",
        ],
        "psc_risk": "HIGH — Code 15 deficiency; STCW and MLC work/rest violations frequently cited together in PSC inspections",
    },
    # ── ISM Incident Severity Classification ──────────────────────────────────
    {
        "id": "ism-incident-severity",
        "topic": "ism incident severity classification high medium low serious accident near miss injury pollution grounding collision fire 24 hour notification",
        "regulation": "ISM Code Section 9 + IMO Resolution A.1048(27)",
        "clause": "MSC-MEPC.7/Circ.7 — Casualty and Near-Miss Reporting",
        "text": (
            "Maritime incident severity classification for ISM reporting purposes: "
            "HIGH SEVERITY (Serious Marine Casualty) — mandatory 24-hour flag state notification: "
            "  - Total loss of vessel; "
            "  - Loss of life or missing person; "
            "  - Injury requiring medical treatment (hospitalisation); "
            "  - Structural damage affecting seaworthiness (hull breach, flooding); "
            "  - Grounding or stranding; "
            "  - Collision with another vessel or fixed structure; "
            "  - Fire or explosion causing structural damage; "
            "  - Pollution event (oil spill to sea, MARPOL violation). "
            "MEDIUM SEVERITY (Marine Incident) — report to company within 24h, flag state within 72h: "
            "  - Near-miss with potential for HIGH outcome; "
            "  - Equipment failure affecting safety systems (lifeboat, fire suppression, navigation); "
            "  - Injury NOT requiring hospitalisation; "
            "  - Contained spill (no sea pollution). "
            "LOW SEVERITY (Non-conformance / Hazardous Situation): "
            "  - Procedural deviation with no safety consequence; "
            "  - Minor equipment defect not affecting seaworthiness; "
            "  - Near-miss with low potential outcome. "
            "HIGH severity incidents overdue review (>24h since report) trigger departure block. "
            "MEDIUM incidents overdue >72h also trigger departure block. "
            "Near-miss reports CANNOT be deleted — ISM audit trail requirement."
        ),
        "validity_years": None,
        "test_implications": [
            "High severity incident reported = Notify Authority checkbox mandatory (24h deadline)",
            "High severity + 24h elapsed without notification = departure-block banner must appear",
            "Medium severity + 72h elapsed without review = departure-block banner must appear",
            "Low severity: no departure block regardless of review status",
            "Incident type 'Collision' or 'Grounding' or 'Injury' = auto-assign High severity",
            "Incident type 'Near Miss' = can be Low or Medium depending on potential — test both",
            "Delete attempt on any near-miss incident = system must reject with error",
            "Review submitted without root cause text = system must reject submission",
            "Status 'Approved' only reachable after review submitted — test direct status change rejected",
            "Notify Authority checked = flag state notification logged in audit trail",
        ],
        "psc_risk": "CRITICAL — Unreported serious casualties = criminal liability; ISM non-conformance without corrective action = detention",
    },
    # ── Bunker Consumption Formula ─────────────────────────────────────────────
    {
        "id": "bunker-consumption-formula",
        "topic": "bunker fuel consumption calculation formula voyage planning distance speed fuel rate margin adequacy warning critical threshold",
        "regulation": "SOLAS Chapter II-1 Regulation 26 + INTERTANKO Bunker Sufficiency Guidelines",
        "clause": "INTERTANKO/BIMCO Bunker Planning Best Practice 2019",
        "text": (
            "Bunker consumption calculation for voyage planning: "
            "Formula: Estimated Consumption (MT) = (Distance nm ÷ Speed knots) × Daily Fuel Rate (MT/day) ÷ 24. "
            "Example: 8500 nm ÷ 14 knots × 45 MT/day ÷ 24 = 1127 MT estimated consumption. "
            "Bunker Margin on Arrival = ((Bunker Loaded MT − Estimated Consumption MT) ÷ Bunker Loaded MT) × 100. "
            "Adequacy thresholds (INTERTANKO/BIMCO industry standard): "
            "  ADEQUATE (green): arrival margin > 15% of loaded bunker. "
            "  WARNING (yellow): arrival margin 5%–15% — remedial action recommended. "
            "  CRITICAL (red, P1 safety): arrival margin < 5% — propulsion failure risk. "
            "  INVALID: bunker quantity = 0 MT or negative — must be rejected by validation. "
            "Boundary values: exactly 15% = ADEQUATE (not Warning); exactly 5% = WARNING (not Critical). "
            "Speed has non-linear effect: reducing speed 10% reduces fuel consumption ~27% (cube law). "
            "Weather deviation adds 5–15% to consumption — voyage plan must account for deviation margin. "
            "Fuel types and approximate consumption rates: VLSFO ~45 MT/day at 14kn; MGO ~42 MT/day; LNG ~38 MT/day equivalent."
        ),
        "validity_years": None,
        "test_implications": [
            "0 MT bunker input = validation error — submit button must be disabled or form rejected",
            "Negative bunker = validation error — same rejection as zero",
            "Calculated margin exactly 15% = ADEQUATE badge (green) — not Warning",
            "Calculated margin exactly 5% = WARNING badge (yellow) — not Critical",
            "Calculated margin 14.9% = WARNING (just below ADEQUATE threshold)",
            "Calculated margin 4.9% = CRITICAL badge (red) — safety-critical P1 scenario",
            "8500 nm at 14 knots with 1500 MT bunker: consumption ~1127 MT, margin ~25% = ADEQUATE",
            "8500 nm at 14 knots with 1200 MT bunker: consumption ~1127 MT, margin ~6% = WARNING",
            "Speed field empty or zero = form validation error before submission",
            "Distance field zero = validation error (cannot plan zero-distance voyage)",
            "LNG fuel type: test ECA compliance not required (LNG = zero sulphur)",
        ],
        "psc_risk": "CRITICAL — Insufficient bunker causing propulsion failure = distress situation, SOLAS violation",
    },
    # ── ECA Fuel Switch Timing ─────────────────────────────────────────────────
    {
        "id": "marpol-eca-fuel-switch-timing",
        "topic": "marpol eca fuel switch timing 1 hour before entry transition vlsfo mgo sulphur eca boundary",
        "regulation": "MARPOL Annex VI Regulation 14.6",
        "clause": "Regulation 14.6 + MEPC.1/Circ.878 — Fuel Changeover Procedures",
        "text": (
            "When a vessel enters an Emission Control Area (ECA), fuel switch from VLSFO (0.5%) to "
            "compliant fuel (MGO 0.1%) must be completed AT LEAST 1 HOUR BEFORE the vessel crosses "
            "the ECA boundary. Regulation 14.6 requires the vessel to maintain a Fuel Oil Changeover "
            "Procedure (FOCP) logbook entry recording: time of switch, position, fuel grade before and after. "
            "ECAs where fuel switch is mandatory: North Sea SOx ECA, Baltic Sea SOx ECA, "
            "English Channel, North American ECA (200nm from coast), US Caribbean ECA. "
            "Vessels carrying VLSFO into an ECA face MARPOL Annex VI prosecution even if the fuel switch "
            "was performed on crossing the boundary (not 1 hour before). "
            "LNG-fuelled vessels are exempt from sulphur ECA requirements (zero sulphur emissions). "
            "Vessels with approved scrubbers may use HFO inside ECA — scrubber status must be verified before entry."
        ),
        "validity_years": None,
        "test_implications": [
            "Route enters North Sea/Baltic/English Channel + VLSFO = ECA non-compliance warning badge",
            "Route enters ECA + MGO = ECA compliant — no warning badge",
            "Route enters ECA + LNG = ECA compliant (LNG exempt) — no warning badge",
            "Route with NO ECA zones + VLSFO = no ECA warning (VLSFO compliant globally)",
            "ECA badge count on voyage table: count of ECA zones the route passes through",
            "Zero ECA zones = green 'None' badge on voyage table row",
            "Fuel switch alert timing: must trigger 1h before ECA boundary, not at boundary",
            "Voyage details panel must show ECA zone compliance status per zone",
            "VLSFO + no scrubber + ECA route = ECA compliance status 'Non-Compliant'",
        ],
        "psc_risk": "HIGH — MARPOL Annex VI violation, flag state prosecution, port detention and fines",
    },
    # ── PSC Concentrated Inspection ───────────────────────────────────────────
    {
        "id": "psc-concentrated-inspection",
        "topic": "psc port state control concentrated inspection targeting risk profile deficiency history age flag",
        "regulation": "Paris MOU Memorandum of Understanding + Tokyo MOU",
        "clause": "Paris MOU — New Inspection Regime (NIR), Target Factor Calculation",
        "text": (
            "PSC concentrated inspection criteria (Paris MOU New Inspection Regime): "
            "A vessel is selected for CONCENTRATED INSPECTION (all areas, longer duration) when: "
            "1. THREE OR MORE deficiencies recorded in the last 36 months; OR "
            "2. ONE OR MORE detentions in the last 36 months; OR "
            "3. Vessel age > 12 years (increased structural risk); OR "
            "4. Flag State performance rating: BLACK LIST or GREY LIST flag; OR "
            "5. Classification society performance: below-average deficiency rate. "
            "High-priority vessels (Black List flags, 2023): Cook Islands, Comoros, Tuvalu, Palau, Sierra Leone. "
            "WHITE LIST flags (lower inspection frequency): Bahamas, Marshall Islands, Panama, Singapore, Norway. "
            "Target Factor: calculated score 0–3+ from deficiency history, age, flag, class — higher = higher PSC risk. "
            "Vessels with Target Factor > 1.5 are prioritised for inspection at every port call. "
            "ISM non-conformance without corrective action documented = automatic detention trigger."
        ),
        "validity_years": None,
        "test_implications": [
            "Vessel with 3 deficiencies in 36 months = concentrated inspection flag — show elevated PSC risk badge",
            "Single detention in history = concentrated inspection — same escalation as 3 deficiencies",
            "Age > 12 years = add PSC risk warning to voyage/departure check",
            "Black list flag = P1 PSC risk — all features must show elevated PSC risk indicator",
            "Incident not closed with corrective action = auto detention risk — test incident closure validation",
            "ISM non-conformance open > 30 days = concentrated inspection trigger",
            "Target Factor > 1.5 = departure check must include PSC risk alert",
        ],
        "psc_risk": "CRITICAL — Concentrated inspection = high probability of detention; commercial pressure to avoid",
    },
    # ── SMC / DOC Validity ─────────────────────────────────────────────────────
    {
        "id": "ism-smc-doc-validity",
        "topic": "ism safety management certificate smc document of compliance doc validity annual verification renewal 5 year cycle",
        "regulation": "ISM Code Regulation 13 + SOLAS Chapter IX",
        "clause": "ISM Code Section 13 — Certification, Verification and Control",
        "text": (
            "Safety Management Certificate (SMC): issued to each vessel — valid 5 years, "
            "subject to ANNUAL VERIFICATION by flag State or recognised organisation. "
            "If annual verification is NOT completed within 3 months of anniversary date, the SMC is suspended. "
            "Suspended SMC = vessel cannot operate commercially — departure must be blocked. "
            "Document of Compliance (DOC): issued to the shipping company — valid 5 years. "
            "DOC annual verification required within 3 months of anniversary. "
            "Expired DOC = ALL vessels under that company lose their SMC validity automatically. "
            "ISM Audit cycle: Initial certification → annual intermediate verification → 5-year renewal. "
            "Any major non-conformance found during audit = SMC/DOC suspended until corrective action verified. "
            "Difference from crew certs: SMC/DOC applies to the VESSEL and COMPANY, not individual seafarers."
        ),
        "validity_years": 5,
        "test_implications": [
            "SMC expired = departure block — separate from crew cert expiry, affects entire vessel",
            "SMC annual verification overdue (>3 months past anniversary) = SMC suspended = departure block",
            "DOC expired = SMC invalid = departure block — test company-level expiry cascades to vessel",
            "SMC expiry warning at T-30 days = warning banner (same pattern as crew certs)",
            "SMC and crew certs can both be expired simultaneously — test compound departure block (multiple banners)",
            "ISM major non-conformance = SMC suspended — test non-conformance triggers vessel block",
            "Renewal of SMC requires flag state surveyor visit — test 'survey scheduled' status workflow",
        ],
        "psc_risk": "CRITICAL — Vessel without valid SMC cannot legally trade; immediate detention if found operating without SMC",
    },
]


class MaritimeKnowledgeBase:

    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=DB_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection("maritime_regulations")
        # Always upsert so new entries added to REGULATIONS are picked up on restart
        self._seed()

    def _seed(self) -> None:
        ids, docs, metas = [], [], []
        for r in REGULATIONS:
            ids.append(r["id"])
            docs.append(f"{r['topic']} {r['text']}")
            metas.append({
                "topic":       r["topic"],
                "regulation":  r["regulation"],
                "clause":      r["clause"],
                "text":        r["text"][:600],
                "implications": json.dumps(r.get("test_implications", [])),
                "psc_risk":    r.get("psc_risk", "UNKNOWN"),
                "cert_type":   r.get("certificate_type", ""),
                "validity_yrs": str(r.get("validity_years") or ""),
            })
        self._col.upsert(ids=ids, documents=docs, metadatas=metas)

    def query(self, topic: str, n_results: int = 5) -> list[dict]:
        count = self._col.count()
        if count == 0:
            return []
        res = self._col.query(query_texts=[topic], n_results=min(n_results, count))
        out = []
        for i, meta in enumerate(res["metadatas"][0]):
            psc = meta.get("psc_risk", "")
            out.append({
                "id":            res["ids"][0][i],
                "title":         f"{meta['regulation']} — {meta['clause']}",
                "convention":    self._extract_convention(meta["regulation"]),
                "content":       meta["text"],
                "severity":      self._extract_severity(psc),
                "applies_to":    json.loads(meta.get("implications", "[]"))[:3],
                # legacy fields kept for Agent 1 compatibility
                "regulation":    meta["regulation"],
                "clause":        meta["clause"],
                "text":          meta["text"],
                "implications":  json.loads(meta.get("implications", "[]")),
                "psc_risk":      psc,
                "cert_type":     meta.get("cert_type", ""),
                "validity_years": meta.get("validity_yrs", ""),
                "similarity":    round(1 - res["distances"][0][i], 3),
            })
        return out

    def get_all(self) -> list[dict]:
        res = self._col.get(include=["metadatas"])
        out = []
        for i in range(len(res["ids"])):
            meta = res["metadatas"][i]
            psc  = meta.get("psc_risk", "")
            out.append({
                "id":         res["ids"][i],
                "title":      f"{meta['regulation']} — {meta['clause']}",
                "convention": self._extract_convention(meta["regulation"]),
                "content":    meta.get("text", ""),
                "severity":   self._extract_severity(psc),
                "applies_to": json.loads(meta.get("implications", "[]"))[:3],
                "psc_risk":   psc,
            })
        return out

    @staticmethod
    def _extract_convention(regulation: str) -> str:
        reg = regulation.upper()
        for conv in ("STCW", "MLC", "MARPOL", "SOLAS", "ISM", "FAL", "BMP5", "ISPS", "IMO", "PSC", "INTERTANKO", "BIMCO"):
            if conv in reg:
                return conv
        return "IMO"

    @staticmethod
    def _extract_severity(psc_risk: str) -> str:
        r = psc_risk.upper()
        if "CRITICAL" in r: return "CRITICAL"
        if "HIGH"     in r: return "HIGH"
        if "MEDIUM"   in r: return "MEDIUM"
        if "LOW"      in r: return "LOW"
        return "MEDIUM"

    def count(self) -> int:
        return self._col.count()

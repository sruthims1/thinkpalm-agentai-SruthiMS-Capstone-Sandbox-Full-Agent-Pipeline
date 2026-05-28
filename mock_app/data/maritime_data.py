from datetime import date

CREW_DATA = [
    {"id": 1, "name": "Capt. James Whitfield", "rank": "Master",          "cert": "Certificate of Competency - Master", "expiry": "2026-05-30", "status": "expiring_soon"},
    {"id": 2, "name": "Ivan Petrov",           "rank": "Chief Officer",   "cert": "STCW Basic Safety Training",          "expiry": "2026-06-07", "status": "expiring_soon"},
    {"id": 3, "name": "Maria Santos",          "rank": "2nd Officer",     "cert": "Medical Fitness Certificate",         "expiry": "2027-03-15", "status": "valid"},
    {"id": 4, "name": "Tom Walsh",             "rank": "Chief Engineer",  "cert": "GMDSS Operator Certificate",          "expiry": "2025-11-01", "status": "expired"},
    {"id": 5, "name": "Ravi Kumar",            "rank": "2nd Engineer",    "cert": "Certificate of Competency - Engineer","expiry": "2026-12-20", "status": "valid"},
    {"id": 6, "name": "Chen Wei",              "rank": "3rd Officer",     "cert": "STCW Advanced Fire Fighting",         "expiry": "2026-05-25", "status": "expiring_soon"},
]

FATIGUE_DATA = [
    {"id": 1, "name": "Capt. James Whitfield", "rank": "Master",        "rest_24h": 9.5,  "rest_7d": 72, "min_rest_24h": 10, "min_rest_7d": 77, "status": "violation",  "watch": "00:00-04:00"},
    {"id": 2, "name": "Ivan Petrov",           "rank": "Chief Officer", "rest_24h": 11.0, "rest_7d": 80, "min_rest_24h": 10, "min_rest_7d": 77, "status": "compliant",  "watch": "04:00-08:00"},
    {"id": 3, "name": "Maria Santos",          "rank": "2nd Officer",   "rest_24h": 10.5, "rest_7d": 78, "min_rest_24h": 10, "min_rest_7d": 77, "status": "compliant",  "watch": "08:00-12:00"},
    {"id": 4, "name": "Chen Wei",              "rank": "3rd Officer",   "rest_24h": 9.0,  "rest_7d": 70, "min_rest_24h": 10, "min_rest_7d": 77, "status": "violation",  "watch": "12:00-16:00"},
    {"id": 5, "name": "Ravi Kumar",            "rank": "2nd Engineer",  "rest_24h": 10.0, "rest_7d": 77, "min_rest_24h": 10, "min_rest_7d": 77, "status": "compliant",  "watch": "16:00-20:00"},
]

PORT_CALLS = [
    {
        "id": 1,
        "vessel": "MV Oceanic Pioneer",
        "port": "Port of Rotterdam",
        "country": "Netherlands",
        "eta": "2026-06-10 06:00",
        "etd": "2026-06-12 18:00",
        "pre_arrival_96h": "submitted",
        "pre_arrival_24h": "pending",
        "customs_clearance": "pending",
        "dangerous_goods": "none",
        "agent": "Boskalis Maritime Services",
        "status": "pre_arrival"
    },
    {
        "id": 2,
        "vessel": "MV Star Nour",
        "port": "Port of Singapore",
        "country": "Singapore",
        "eta": "2026-06-15 14:00",
        "etd": "2026-06-17 08:00",
        "pre_arrival_96h": "submitted",
        "pre_arrival_24h": "submitted",
        "customs_clearance": "approved",
        "dangerous_goods": "declared",
        "agent": "Pacific Carriers Agency",
        "status": "in_port"
    },
]

INCIDENTS = [
    {
        "id": "INC-2026-001",
        "type": "Near Miss",
        "severity": "High",
        "date": "2026-05-20",
        "vessel": "MV Oceanic Pioneer",
        "location": "Engine Room",
        "description": "Engineer slipped near main engine due to oil spillage. No injury but high fall risk.",
        "reported_by": "Ravi Kumar",
        "status": "pending_review",
        "officer_review": None,
        "superintendent_approval": None,
        "authority_notified": False,
        "deadline": "2026-05-21"
    },
    {
        "id": "INC-2026-002",
        "type": "Incident",
        "severity": "Medium",
        "date": "2026-05-18",
        "vessel": "MV Star Nour",
        "location": "Deck",
        "description": "Mooring line parted during berthing operation at Rotterdam.",
        "reported_by": "Ivan Petrov",
        "status": "approved",
        "officer_review": "Reviewed - equipment fatigue identified",
        "superintendent_approval": "Approved - replacement ordered",
        "authority_notified": True,
        "deadline": "2026-05-19"
    },
]

VOYAGES = [
    {
        "id": "VOY-2026-045",
        "vessel": "MV Oceanic Pioneer",
        "departure_port": "Port of Houston",
        "arrival_port": "Port of Rotterdam",
        "departure_date": "2026-06-01",
        "eta": "2026-06-15",
        "distance_nm": 5420,
        "speed_kts": 14.5,
        "fuel_type": "VLSFO",
        "bunker_qty_mt": 1850,
        "eca_zones": ["North Sea ECA", "English Channel ECA"],
        "waypoints": ["Gulf of Mexico", "Atlantic Ocean", "English Channel"],
        "status": "planned",
        "weather_routing": "optimal",
        "piracy_alert": False
    },
    {
        "id": "VOY-2026-046",
        "vessel": "MV Star Nour",
        "departure_port": "Port of Singapore",
        "arrival_port": "Port of Chiba",
        "departure_date": "2026-06-17",
        "eta": "2026-06-22",
        "distance_nm": 3320,
        "speed_kts": 13.0,
        "fuel_type": "VLSFO",
        "bunker_qty_mt": 980,
        "eca_zones": [],
        "waypoints": ["Malacca Strait", "South China Sea", "Pacific Ocean"],
        "status": "active",
        "weather_routing": "weather_deviation",
        "piracy_alert": True
    },
]

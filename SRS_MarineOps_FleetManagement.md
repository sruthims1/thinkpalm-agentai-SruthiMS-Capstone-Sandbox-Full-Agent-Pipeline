# Software Requirements Specification (SRS)
## MarineOps — Fleet Management System
**Version:** 1.0  
**Prepared by:** ThinkPalm Technologies Ltd  
**Date:** 23 May 2026  
**Status:** Draft

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Features & Functional Requirements](#3-system-features--functional-requirements)
   - 3.1 Crew Certification Management
   - 3.2 Crew Fatigue Management
   - 3.3 Port Call Management
   - 3.4 Incident & Near-Miss Reporting
   - 3.5 Voyage Planning
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [External Interface Requirements](#5-external-interface-requirements)
6. [Constraints & Assumptions](#6-constraints--assumptions)
7. [Appendix — Regulatory References](#7-appendix--regulatory-references)

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification defines the functional and non-functional requirements for the **MarineOps Fleet Management System** — a web-based maritime operations platform used by fleet managers, vessel masters, and shore-based superintendents to manage crew compliance, port operations, safety incidents, and voyage planning across a managed fleet.

### 1.2 Scope
The system covers the following five operational modules:
- Crew Certification & Compliance Management
- Crew Fatigue & Rest Hours Management
- Port Call Management
- Incident & Near-Miss Reporting
- Voyage Planning

The system does **not** cover cargo planning, load calculations, commercial voyage operations, or integration with external AIS tracking providers in this version.

### 1.3 Definitions & Acronyms

| Term | Definition |
|------|-----------|
| STCW | Standards of Training, Certification and Watchkeeping for Seafarers (IMO Convention) |
| MLC 2006 | Maritime Labour Convention 2006 — international seafarer rights and working conditions treaty |
| ISM Code | International Safety Management Code — mandatory safety management framework |
| ISPS Code | International Ship and Port Facility Security Code |
| ECA | Emission Control Area — sea zones with strict sulphur emission limits |
| FAL | Facilitation of International Maritime Traffic — standardised port clearance forms |
| IMO | International Maritime Organisation |
| PSC | Port State Control — port authority inspection of foreign vessels |
| VLSFO | Very Low Sulphur Fuel Oil (max 0.5% sulphur) |
| MGO | Marine Gas Oil (ECA-compliant fuel, max 0.1% sulphur) |
| ETA | Estimated Time of Arrival |
| ETD | Estimated Time of Departure |
| GM | Metacentric Height — measure of vessel stability |
| Master | Vessel captain — highest authority on board |
| Superintendent | Shore-based technical/operations manager |

### 1.4 Overview
This document is organised as follows: Section 2 provides a high-level product description. Section 3 details functional requirements per module. Section 4 covers non-functional requirements. Sections 5–7 cover interfaces, constraints, and regulatory references.

---

## 2. Overall Description

### 2.1 Product Perspective
MarineOps is a standalone web-based fleet management application. It operates as a centralised platform accessible to both shore-based operations teams and vessel personnel. The system is built on a client-server architecture with a web UI, REST API, and persistent data store.

### 2.2 Product Functions — Summary

| Module | Primary Function |
|--------|-----------------|
| Crew Certification | Track STCW certificate validity; alert on expiry; block departure on expired certs |
| Fatigue Management | Monitor MLC 2006 rest hours; flag violations; trigger watch reassignment |
| Port Call Management | Manage pre-arrival notifications, FAL documentation, customs clearance workflow |
| Incident Reporting | Multi-role incident submission, review, and authority notification workflow |
| Voyage Planning | Plan voyages with route waypoints, ECA zone detection, fuel estimates, piracy alerts |

### 2.3 User Classes

| Role | Description | Access Level |
|------|-------------|-------------|
| Fleet Manager | Shore-based; oversees all vessels | Full access — all modules, all vessels |
| Superintendent | Shore-based; approves incidents, monitors compliance | Read/approve — all modules |
| Master (Captain) | On board; highest vessel authority | Full access — own vessel |
| Chief Officer | On board; manages crew and cargo | Crew, fatigue, incidents — own vessel |
| Crew Member | On board; reports incidents, logs rest | Incident reporting, own fatigue records |

### 2.4 Operating Environment
- Web browser (Chrome, Firefox, Edge — latest two versions)
- Responsive layout supporting desktop and tablet
- Server: Python Flask application on Linux/Windows server
- Data: In-memory store for mock; persistent relational database in production

### 2.5 Assumptions
- All dates and times are stored and displayed in UTC
- The system manages a fleet of up to 50 vessels
- Vessel data (IMO number, vessel type, flag state) is pre-configured
- User authentication is handled externally (out of scope for this version)

---

## 3. System Features & Functional Requirements

---

### 3.1 Crew Certification Management

#### 3.1.1 Description
The system shall maintain a register of STCW and flag-state mandated certificates for all crew members. It shall automatically calculate certificate validity, generate alerts, and enforce departure blocks when required.

#### 3.1.2 Functional Requirements

**FR-CC-01 — Certification Register**
The system shall maintain a certification register containing:
- Crew member name and rank
- Certificate type (e.g., CoC Master, STCW Basic Safety, GMDSS, Medical Fitness)
- Certificate number
- Issue date and expiry date
- Current validity status

**FR-CC-02 — Automatic Status Calculation**
The system shall automatically calculate and assign one of three statuses based on today's date:
- `Valid` — expiry date is more than 30 days away
- `Expiring Soon` — expiry date is within 30 days
- `Expired` — expiry date has passed

**FR-CC-03 — Expiry Alert — 30-Day Warning**
The system shall display a prominent warning banner for any crew member whose certificate expires within 30 days.

**FR-CC-04 — Expiry Alert — 7-Day Warning**
The system shall escalate the alert to a critical warning when expiry is within 7 days, and send a notification to the fleet manager and superintendent.

**FR-CC-05 — Departure Block**
The system shall display a **VESSEL DEPARTURE BLOCKED** banner when any crew member on a scheduled departure has an expired certificate. The vessel departure shall not be confirmable until the block is resolved.

**FR-CC-06 — Certificate Renewal**
An authorised user shall be able to update a certificate record with:
- New expiry date
- New certificate number
Upon submission, the system shall recalculate the status and remove any active departure block if resolved.

**FR-CC-07 — Status Filter**
The system shall provide a filter to display crew by status: All / Expired / Expiring Soon / Valid.

**FR-CC-08 — Days Remaining Display**
The system shall display the number of days remaining (or days overdue) for each certificate in the register.

#### 3.1.3 Business Rules

| Rule | Description |
|------|-------------|
| BR-CC-01 | Minimum 1 valid Medical Fitness Certificate required per vessel at all times |
| BR-CC-02 | GMDSS certificate must be held by at least one navigating officer per watch |
| BR-CC-03 | Expired certificates cannot be overridden without superintendent authorisation |

#### 3.1.4 Edge Cases for Testing
- Certificate expires exactly today (days_remaining = 0) → must show `Expired`
- Certificate expires in exactly 30 days → must show `Expiring Soon`
- Certificate expires in 31 days → must show `Valid`
- Multiple crew members with expired certs → departure block shows all names
- Renewing one expired cert when another remains expired → departure block persists

---

### 3.2 Crew Fatigue Management

#### 3.2.1 Description
The system shall track officer and crew rest hours in compliance with MLC 2006 and STCW requirements to prevent fatigue-related accidents. It shall detect violations, alert responsible parties, and support watch reassignment.

#### 3.2.2 Functional Requirements

**FR-FM-01 — Rest Hours Register**
The system shall maintain a rest hours register per officer showing:
- Name and rank
- Assigned watch schedule
- Total rest hours in last 24 hours
- Total rest hours in last 7 days
- Compliance status

**FR-FM-02 — MLC Compliance Rules Enforcement**
The system shall enforce the following minimum rest requirements:
- Minimum **10 hours** rest in any 24-hour period
- Minimum **77 hours** rest in any 7-day period
- Rest may be divided into no more than 2 periods, one of which shall be at least 6 hours

**FR-FM-03 — Violation Detection**
The system shall automatically flag a crew member as `Violation` if any MLC rule is breached and display a prominent alert on the fatigue management page.

**FR-FM-04 — Watch Reassignment Trigger**
When a violation is detected, the system shall display a **Reassign Watch** action for the affected officer. Triggering this action shall log a reassignment event and notify the Chief Officer.

**FR-FM-05 — Log Rest Hours**
Authorised users shall be able to log a rest period for any officer by specifying:
- Officer name
- Rest period start datetime
- Rest period end datetime
The system shall validate that the end time is after the start time.

**FR-FM-06 — Compliance Summary**
The fatigue page shall display aggregate counts of: total officers tracked, compliant officers, and active violations.

**FR-FM-07 — PSC Audit Risk Indicator**
The system shall display an audit risk level (Low / Medium / High) based on the number of active violations. Two or more violations shall trigger `High` risk.

#### 3.2.3 Business Rules

| Rule | Description |
|------|-------------|
| BR-FM-01 | Emergency or distress situations may override rest hour requirements. Override requires Master's written authorisation and must be logged |
| BR-FM-02 | Port State Control inspectors may request the last 3 months of rest hour records |
| BR-FM-03 | Violations must be rectified before a new watch assignment can be confirmed |

#### 3.2.4 Edge Cases for Testing
- Rest period spanning midnight (e.g., 22:00–06:00) — must count as single continuous period
- Officer logs exactly 10 hours rest → status must be `Compliant`, not `Violation`
- Officer logs 9 hours 59 minutes → status must be `Violation`
- Rest period end time entered before start time → validation error displayed
- All officers compliant → PSC risk shows `Low`, no violation banners shown

---

### 3.3 Port Call Management

#### 3.3.1 Description
The system shall manage the full port call lifecycle for each vessel visit, from pre-arrival notification through to port clearance and departure.

#### 3.3.2 Functional Requirements

**FR-PC-01 — Port Call Register**
The system shall maintain a register of all port calls with:
- Vessel name
- Port name and country
- ETA and ETD
- Pre-arrival notification status (96-hour and 24-hour)
- Customs clearance status
- Dangerous goods declaration status
- Port agent details
- Current status (Pre-Arrival / In Port / Completed)

**FR-PC-02 — Create Port Call**
An authorised user shall be able to create a new port call record by providing:
- Vessel, port, ETA, ETD, dangerous goods flag, agent name

**FR-PC-03 — 96-Hour Pre-Arrival Notice**
The system shall track submission of the 96-hour pre-arrival notification. Unsubmitted notices shall be highlighted in red on the register.

**FR-PC-04 — 24-Hour Pre-Arrival Notice**
The system shall allow users to submit the 24-hour pre-arrival notice by entering:
- Agent name, expected cargo quantity, last port of call
Upon submission, the notice status shall update to `Submitted`.

**FR-PC-05 — FAL Document Checklist**
The system shall display a checklist of standard FAL documents:
- FAL Form 1 (General Declaration)
- FAL Form 5 (Crew List)
- FAL Form 6 (Passenger List)
- Dangerous Goods Declaration (if applicable)

**FR-PC-06 — Customs Clearance Status**
The system shall display customs clearance status per port call: Pending / Approved / Rejected.

**FR-PC-07 — Dangerous Goods Flag**
When a port call is created with dangerous goods declared, the system shall display a warning and require a dangerous goods declaration to be submitted before departure.

#### 3.3.3 Business Rules

| Rule | Description |
|------|-------------|
| BR-PC-01 | 96-hour notice is mandatory for all EU port entries |
| BR-PC-02 | 24-hour notice is mandatory for all ISPS-compliant ports |
| BR-PC-03 | Dangerous goods on board must be declared before vessel enters port waters |
| BR-PC-04 | Customs clearance must be `Approved` before cargo operations can commence |

#### 3.3.4 Edge Cases for Testing
- ETA entered in the past → validation warning displayed
- ETD entered before ETA → validation error displayed
- Dangerous goods declared but declaration not submitted → cannot progress to In Port status
- Submitting 24h notice when 96h notice is still pending → warning displayed
- Port call created without an agent → system flags as incomplete

---

### 3.4 Incident & Near-Miss Reporting

#### 3.4.1 Description
The system shall provide a multi-role incident reporting and review workflow compliant with the ISM Code. It shall track all safety incidents from initial report through officer review, superintendent approval, and maritime authority notification.

#### 3.4.2 Functional Requirements

**FR-IR-01 — Incident Register**
The system shall maintain an incident register displaying:
- Incident ID (auto-generated, e.g., INC-2026-001)
- Type (Near Miss / Incident / Accident)
- Severity (Low / Medium / High)
- Date and vessel
- Location on vessel
- Current workflow status
- Authority notification status

**FR-IR-02 — Report Incident**
Any authenticated user shall be able to submit an incident report containing:
- Incident type, severity, vessel, location on vessel
- Detailed description
Upon submission, status is set to `Pending Review` and a review deadline is assigned.

**FR-IR-03 — Incident ID Auto-Generation**
The system shall auto-generate a unique incident ID in the format `INC-YYYY-NNN` upon submission.

**FR-IR-04 — Officer Review**
An officer shall be able to review a pending incident by entering:
- Review comments
- Root cause classification
- Authority notification decision
Upon submission, status updates to `Approved`.

**FR-IR-05 — Overdue Review Alert**
The system shall display a prominent **OVERDUE REVIEW** banner for any incident where:
- Status is `Pending Review`, AND
- Review deadline has passed

**FR-IR-06 — Authority Notification**
For High severity incidents, the system shall:
- Require maritime authority notification within 24 hours of incident
- Display the authority notification status on the register
- Flag as overdue if not notified within 24 hours

**FR-IR-07 — Incident Statistics**
The system shall display aggregate counts: total incidents, high severity, pending review, and closed (approved).

#### 3.4.3 Business Rules

| Rule | Description |
|------|-------------|
| BR-IR-01 | High severity incidents must be reported to flag state authority within 24 hours (ISM Code requirement) |
| BR-IR-02 | Near-miss reports must be reviewed by a qualified officer within 24 hours |
| BR-IR-03 | Accident reports require superintendent approval before closure |
| BR-IR-04 | A minimum of 12 months of incident records must be retained on board |

#### 3.4.4 Edge Cases for Testing
- High severity incident reported → authority notification checkbox must be pre-selected
- Incident review submitted without officer comments → validation error
- Incident deadline passed but status still `Pending Review` → overdue banner appears
- Multiple high severity incidents open simultaneously → all appear in overdue list
- Incident type changes from Near Miss to Accident → authority notification becomes mandatory

---

### 3.5 Voyage Planning

#### 3.5.1 Description
The system shall support the planning of vessel voyages including route waypoints, ECA zone identification, fuel consumption estimates, weather routing alerts, and piracy risk notifications.

#### 3.5.2 Functional Requirements

**FR-VP-01 — Voyage Register**
The system shall maintain a voyage register displaying:
- Voyage ID (auto-generated, e.g., VOY-2026-045)
- Vessel, departure port, arrival port
- Departure date and ETA
- Distance in nautical miles
- Bunker quantity (MT)
- ECA zones on route
- Voyage status (Planned / Active / Completed)

**FR-VP-02 — Create Voyage Plan**
An authorised user shall be able to create a voyage plan by entering:
- Vessel, departure port, arrival port, departure date
- Vessel speed (knots), distance (nautical miles)
- Bunker quantity on board (MT), fuel type

**FR-VP-03 — Voyage ID Auto-Generation**
The system shall auto-generate a unique voyage ID in the format `VOY-YYYY-NNN` upon creation.

**FR-VP-04 — Fuel Consumption Estimate**
The system shall calculate and display:
- Estimated daily fuel consumption (MT/day) based on vessel speed
- Total estimated voyage consumption (MT)
- Remaining bunker margin after voyage
- Adequacy flag: `Adequate` if margin > 15%, `Warning` if margin 5–15%, `Critical` if below 5%

**FR-VP-05 — ECA Zone Detection**
The system shall detect whether the planned route passes through any ECA zones (North Sea, English Channel, Baltic Sea, North American ECA, US Caribbean ECA) and display:
- Number of ECA zones on route
- Required fuel type for ECA compliance (MGO or VLSFO with scrubber)
- Warning if current fuel type is non-compliant for ECA zones on route

**FR-VP-06 — Route Waypoints**
The system shall display the ordered list of waypoints for a voyage from departure to arrival port.

**FR-VP-07 — Weather Routing Alert**
The system shall display a weather deviation alert when the weather routing status is `weather_deviation`, indicating:
- Nature of weather event
- Recommended action (route deviation)
- Revised ETA impact

**FR-VP-08 — Confirm Route Deviation**
A user shall be able to confirm a recommended route deviation. Upon confirmation, the weather routing status updates to `deviation_confirmed` and ETA is revised.

**FR-VP-09 — Piracy Alert**
The system shall display a **PIRACY ALERT** banner for any active voyage flagged as passing through a high-risk area. The alert shall indicate that the IMB Piracy Reporting Centre has been notified and the Master has been advised.

#### 3.5.3 Business Rules

| Rule | Description |
|------|-------------|
| BR-VP-01 | Bunker margin must be at least 15% of total estimated consumption at all times |
| BR-VP-02 | Vessels must switch to ECA-compliant fuel at least 1 hour before entering an ECA zone |
| BR-VP-03 | Piracy-risk voyages require BMP (Best Management Practices) checklist completion before departure |
| BR-VP-04 | Voyage speed must be between 5 and 25 knots; values outside this range are rejected |

#### 3.5.4 Edge Cases for Testing
- Bunker quantity entered as 0 → validation error
- Departure date entered in the past → warning displayed
- Route passes through ECA zone but fuel type is VLSFO without scrubber → compliance warning
- Speed entered as 0 → validation error (division by zero in fuel calculation)
- Speed entered above 25 knots → business rule rejection
- Active voyage with piracy alert — piracy banner must be visible on page load
- Weather deviation confirmed → ETA field updates to show revised estimate

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-P-01:** All page loads shall complete within 2 seconds under normal load (up to 50 concurrent users)
- **NFR-P-02:** API responses shall return within 500ms

### 4.2 Reliability
- **NFR-R-01:** System availability shall be 99.5% uptime during operational hours
- **NFR-R-02:** No data loss shall occur during planned maintenance windows

### 4.3 Security
- **NFR-S-01:** All data transmission shall use HTTPS (TLS 1.2 or above)
- **NFR-S-02:** Role-based access control shall prevent unauthorised access to other vessels' data
- **NFR-S-03:** All form inputs shall be validated server-side to prevent injection attacks

### 4.4 Usability
- **NFR-U-01:** Critical alerts (departure blocks, fatigue violations, overdue incidents) shall be visible without scrolling on a 1366×768 display
- **NFR-U-02:** The system shall provide confirmation feedback within 1 second of any form submission

### 4.5 Maintainability
- **NFR-M-01:** The system shall follow modular architecture — each feature module shall be independently deployable
- **NFR-M-02:** All regulatory thresholds (e.g., 30-day cert warning, 10h rest minimum) shall be configurable without code changes

---

## 5. External Interface Requirements

### 5.1 User Interface
- Web-based UI using Bootstrap 5
- Responsive layout for desktop and tablet
- Consistent sidebar navigation across all modules
- Colour-coded status indicators: Red (critical/expired/violation), Orange (warning/expiring), Green (valid/compliant)

### 5.2 API Interface
The system shall expose the following REST API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crew` | GET | Returns all crew certification records |
| `/api/fatigue` | GET | Returns all fatigue/rest hour records |
| `/api/incidents` | GET | Returns all incident records |
| `/api/voyages` | GET | Returns all voyage records |

### 5.3 Data Format
- All API responses shall be in JSON format
- All dates shall use ISO 8601 format (YYYY-MM-DD)
- All datetimes shall use ISO 8601 with UTC offset (YYYY-MM-DDTHH:MM:SSZ)

---

## 6. Constraints & Assumptions

### 6.1 Constraints
- The system operates as a mock/demo environment; data is in-memory and resets on server restart
- No external AIS, weather API, or port authority system integration in this version
- Authentication and authorisation are out of scope for the mock application
- All regulatory thresholds are based on IMO/MLC 2006 standards current as of 2026

### 6.2 Assumptions
- All vessels in the system are registered under a flag state that has ratified MLC 2006
- Port call pre-arrival notification periods (96h, 24h) are standard; port-specific variations are not modelled
- Fuel consumption rates are representative estimates; actual values vary by vessel and sea state
- Incident review deadlines are calculated as T+24 hours from incident report submission

---

## 7. Appendix — Regulatory References

| Regulation | Scope | Relevant Module |
|------------|-------|----------------|
| STCW Convention (as amended 2010) | Seafarer certification and training standards | Crew Certification |
| MLC 2006 — Regulation 2.3 | Hours of work and rest | Fatigue Management |
| ISM Code (Resolution A.741(18)) | Safety management, incident reporting | Incident Reporting |
| SOLAS Chapter XI-2 / ISPS Code | Port and vessel security | Port Call Management |
| FAL Convention | Facilitation of port formalities | Port Call Management |
| MARPOL Annex VI Regulation 14 | Sulphur emission limits in ECAs | Voyage Planning |
| IMO MSC-FAL.1/Circ.3 | Piracy reporting and BMP | Voyage Planning |
| COLREGS 1972 | Collision regulations at sea | Voyage Planning |

---

*End of Document*  
*MarineOps SRS v1.0 — ThinkPalm Technologies Ltd — May 2026*

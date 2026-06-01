# User Stories — Voyage Planning Module
## MarineOps Fleet Management System
**Version:** 1.0  
**Module:** Voyage Planning  
**Prepared by:** ThinkPalm Technologies Ltd  
**Date:** 23 May 2026

---

## Overview

This document contains user stories and acceptance criteria for the Voyage Planning module of the MarineOps Fleet Management System. Stories are grouped by functional area and follow the standard format:

> *As a [role], I want to [action], so that [business value].*

Acceptance criteria are written in **Given / When / Then** format to enable direct conversion to BDD test cases.

---

## Story List

| Story ID | Title | Priority |
|----------|-------|----------|
| VP-US-01 | View Voyage Register | High |
| VP-US-02 | Create New Voyage Plan | High |
| VP-US-03 | View Voyage Details and Route Waypoints | Medium |
| VP-US-04 | Fuel Consumption Estimation | High |
| VP-US-05 | ECA Zone Compliance Detection | High |
| VP-US-06 | Weather Routing Alert | Medium |
| VP-US-07 | Confirm Route Deviation | Medium |
| VP-US-08 | Piracy Risk Alert | High |
| VP-US-09 | Voyage Plan Form Validation | High |

---

## VP-US-01 — View Voyage Register

**User Story**
> As a **Fleet Manager**,  
> I want to **view all planned and active voyages in a single register**,  
> so that **I can monitor fleet movements and identify voyages that need attention.**

**Priority:** High  
**Module:** Voyage Planning — Register View

---

### Acceptance Criteria

**AC-01-01: Voyage register loads successfully**
```
Given I am on the Voyage Planning page
When the page loads
Then I should see a table listing all voyages
And each row should display: Voyage ID, Vessel, Route, Departure Date, ETA, Distance, Bunker Qty, ECA Zones, Status
```

**AC-01-02: Voyage status is colour-coded**
```
Given voyages exist with different statuses
When I view the voyage register
Then voyages with status "Active" should display a green badge
And voyages with status "Planned" should display a blue badge
And voyages with status "Completed" should display a grey badge
```

**AC-01-03: ECA zone count is displayed**
```
Given a voyage passes through 2 ECA zones
When I view that voyage row in the register
Then the ECA column should display a yellow badge showing "2 ECA"
```

**AC-01-04: Voyage with no ECA zones shows clear indicator**
```
Given a voyage has no ECA zones on its route
When I view that voyage row
Then the ECA column should display a green badge showing "None"
```

**AC-01-05: Details button is present for each voyage**
```
Given the voyage register is displayed
When I look at any voyage row
Then a "Details" button should be visible
And clicking it should reveal the voyage detail panel
```

---

## VP-US-02 — Create New Voyage Plan

**User Story**
> As a **Fleet Manager**,  
> I want to **create a new voyage plan by entering route and operational details**,  
> so that **the vessel's upcoming voyage is formally planned and tracked in the system.**

**Priority:** High  
**Module:** Voyage Planning — Create Plan

---

### Acceptance Criteria

**AC-02-01: New voyage plan can be created via modal form**
```
Given I am on the Voyage Planning page
When I click the "Plan New Voyage" button
Then a modal form should appear
And the form should contain fields: Vessel, Departure Port, Arrival Port, Departure Date, Speed, Bunker Quantity, Distance, Fuel Type
```

**AC-02-02: Voyage ID is auto-generated on creation**
```
Given I fill all required fields in the new voyage form
When I click "Create Voyage Plan"
Then a new voyage record should be created
And the Voyage ID should be auto-generated in the format VOY-YYYY-NNN
And the new voyage should appear in the register with status "Planned"
```

**AC-02-03: All required fields must be completed**
```
Given I open the new voyage form
When I submit the form without filling the Departure Port field
Then the form should not submit
And a validation error should be displayed on the Departure Port field
```

**AC-02-04: Fuel type defaults to VLSFO**
```
Given I open the new voyage form
When the form loads
Then the Fuel Type dropdown should default to "VLSFO (0.5% Sulphur)"
```

**AC-02-05: New voyage appears immediately in register after creation**
```
Given I successfully create a new voyage plan
When I am redirected to the voyage register
Then the newly created voyage should be visible in the table
And its status should be "Planned"
```

---

## VP-US-03 — View Voyage Details and Route Waypoints

**User Story**
> As a **Master (Captain)**,  
> I want to **view the detailed route waypoints and voyage breakdown for my vessel**,  
> so that **I can brief the bridge team and plan watch assignments accordingly.**

**Priority:** Medium  
**Module:** Voyage Planning — Detail View

---

### Acceptance Criteria

**AC-03-01: Voyage detail panel expands on clicking Details**
```
Given the voyage register is displayed
When I click the "Details" button for a voyage
Then the voyage detail panel should become visible below the register
And the panel should scroll into view automatically
```

**AC-03-02: Route waypoints are displayed in order**
```
Given I view the detail panel for a voyage
When the panel loads
Then the waypoints should be displayed as a numbered ordered list
And the first waypoint should be the departure port
And the last waypoint should be the arrival port
```

**AC-03-03: Piracy-risk waypoints are visually flagged**
```
Given a voyage passes through a piracy-risk waypoint (e.g. Malacca Strait)
When I view the waypoints list
Then that waypoint should display a "Piracy Watch" warning badge
```

**AC-03-04: ECA zone compliance status is shown in detail panel**
```
Given a voyage has no ECA zones
When I view the voyage detail panel
Then the ECA compliance section should display a green success message
And the message should confirm the current fuel type is approved
```

---

## VP-US-04 — Fuel Consumption Estimation

**User Story**
> As a **Superintendent**,  
> I want to **see an estimated fuel consumption breakdown for each voyage**,  
> so that **I can verify adequate bunker quantity is on board before departure.**

**Priority:** High  
**Module:** Voyage Planning — Fuel Planning

---

### Acceptance Criteria

**AC-04-01: Fuel planning table is displayed in voyage detail**
```
Given I view the detail panel for a voyage
When I look at the Fuel Planning section
Then I should see a table showing:
  - Fuel Type
  - Sea Passage Consumption (MT/day)
  - Voyage Days
  - Estimated Total Consumption (MT)
  - Bunker on Board (MT)
  - Remaining Margin (MT) with adequacy indicator
```

**AC-04-02: Adequate bunker margin shows green indicator**
```
Given a voyage has bunker on board of 980 MT
And estimated consumption is 291 MT
When I view the fuel planning table
Then the margin should display as 689 MT
And the adequacy indicator should be green and labelled "adequate"
```

**AC-04-03: Critical bunker margin triggers warning**
```
Given a voyage has bunker on board of 300 MT
And estimated consumption is 291 MT
When I view the fuel planning table
Then the margin should be flagged as "Critical"
And the indicator should be displayed in red
```

**AC-04-04: Zero bunker quantity is rejected at form entry**
```
Given I am creating a new voyage plan
When I enter 0 in the Bunker Quantity field and submit
Then the form should display a validation error
And the voyage should not be created
```

---

## VP-US-05 — ECA Zone Compliance Detection

**User Story**
> As a **Fleet Manager**,  
> I want to **be warned when a planned voyage route passes through ECA zones**,  
> so that **I can ensure the correct low-sulphur fuel is on board before entering the zone.**

**Priority:** High  
**Module:** Voyage Planning — ECA Compliance

---

### Acceptance Criteria

**AC-05-01: ECA zones on route are listed in voyage detail**
```
Given a voyage passes through the North Sea ECA and English Channel ECA
When I view the voyage detail panel
Then both ECA zones should be listed
And the count badge in the register row should show "2 ECA"
```

**AC-05-02: Non-compliant fuel triggers ECA warning**
```
Given a voyage passes through an ECA zone
And the selected fuel type is Heavy Fuel Oil (HFO)
When I view the voyage detail panel
Then a compliance warning should be displayed
And the warning should state that the current fuel is non-compliant for the ECA zones on route
```

**AC-05-03: VLSFO fuel is accepted as ECA-compliant**
```
Given a voyage passes through an ECA zone
And the fuel type is VLSFO (0.5% Sulphur)
When I view the ECA compliance section
Then no compliance warning should be shown
And the status should show as compliant
```

**AC-05-04: Voyage with no ECA zones shows no compliance warning**
```
Given a voyage route does not pass through any ECA zones
When I view the voyage detail panel
Then the ECA section should display a green status
And no fuel-switch warning should appear
```

---

## VP-US-06 — Weather Routing Alert

**User Story**
> As a **Master (Captain)**,  
> I want to **receive a weather routing alert when adverse conditions affect my planned route**,  
> so that **I can make an informed decision on whether to deviate for crew and vessel safety.**

**Priority:** Medium  
**Module:** Voyage Planning — Weather Routing

---

### Acceptance Criteria

**AC-06-01: Weather deviation alert is displayed for affected voyages**
```
Given a voyage has weather_routing status of "weather_deviation"
When I view the voyage detail panel
Then a yellow warning alert should be displayed
And the alert should describe the weather event
And the alert should state the revised ETA impact (e.g. +12 hours)
```

**AC-06-02: Confirm Route Deviation button is visible**
```
Given the weather deviation alert is displayed
When I view the detail panel
Then a "Confirm Route Deviation" button should be visible below the alert
```

**AC-06-03: No weather alert shown for optimal routing**
```
Given a voyage has weather_routing status of "optimal"
When I view the voyage detail panel
Then no weather deviation alert should be displayed
```

---

## VP-US-07 — Confirm Route Deviation

**User Story**
> As a **Master (Captain)**,  
> I want to **formally confirm a recommended route deviation**,  
> so that **the updated route and revised ETA are recorded in the system for shore team visibility.**

**Priority:** Medium  
**Module:** Voyage Planning — Route Deviation

---

### Acceptance Criteria

**AC-07-01: Confirming deviation updates weather routing status**
```
Given a voyage detail panel shows a weather deviation alert
When I click "Confirm Route Deviation"
Then the system should submit the deviation confirmation
And I should be redirected to the voyage page
And a success message should be displayed confirming the deviation
```

**AC-07-02: Deviation confirmation removes the weather alert**
```
Given I have confirmed a route deviation for voyage VOY-2026-046
When I view the voyage detail panel again
Then the weather deviation warning alert should no longer be displayed
```

**AC-07-03: ETA is updated after deviation confirmation**
```
Given a route deviation adds 12 hours to the voyage
When the deviation is confirmed
Then the ETA displayed in the voyage register should reflect the revised estimate
```

---

## VP-US-08 — Piracy Risk Alert

**User Story**
> As a **Fleet Manager**,  
> I want to **see a prominent piracy alert for any active voyage in a high-risk area**,  
> so that **I can verify that the Master has been briefed and BMP procedures are in place.**

**Priority:** High  
**Module:** Voyage Planning — Piracy Alert

---

### Acceptance Criteria

**AC-08-01: Piracy alert banner is displayed on page load**
```
Given an active voyage is flagged with piracy_alert = true
When I navigate to the Voyage Planning page
Then a red PIRACY ALERT banner should be visible at the top of the page
Without any user interaction required
```

**AC-08-02: Piracy alert identifies the specific vessel**
```
Given the piracy alert is displayed
When I read the alert message
Then it should include the vessel name
And it should confirm that the IMB Piracy Reporting Centre has been notified
And it should confirm the Master has been advised
```

**AC-08-03: No piracy alert shown when no voyage is in high-risk area**
```
Given no active voyages are flagged with piracy_alert = true
When I navigate to the Voyage Planning page
Then no piracy alert banner should be displayed
```

**AC-08-04: Multiple piracy alerts shown when multiple voyages affected**
```
Given two active voyages are both flagged with piracy_alert = true
When I navigate to the Voyage Planning page
Then two separate piracy alert banners should be displayed
One for each affected vessel
```

---

## VP-US-09 — Voyage Plan Form Validation

**User Story**
> As a **System**,  
> I want to **validate all inputs when a new voyage plan is created**,  
> so that **invalid or incomplete voyage records cannot be saved to the system.**

**Priority:** High  
**Module:** Voyage Planning — Input Validation

---

### Acceptance Criteria

**AC-09-01: Vessel field is required**
```
Given I open the new voyage form
When I submit the form without selecting a vessel
Then a validation error should appear on the Vessel field
And the form should not be submitted
```

**AC-09-02: Speed must be between 5 and 25 knots**
```
Given I open the new voyage form
When I enter a speed of 30 knots
Then a validation error should appear stating speed must be between 5 and 25 knots
And the voyage should not be created
```

**AC-09-03: Speed of zero is rejected**
```
Given I open the new voyage form
When I enter 0 in the Speed field and submit
Then a validation error should be displayed
And the voyage should not be created
```

**AC-09-04: Departure port and arrival port cannot be the same**
```
Given I open the new voyage form
When I enter "Port of Singapore" for both departure and arrival port
Then a validation error should appear stating departure and arrival ports must be different
```

**AC-09-05: Departure date cannot be in the past**
```
Given I open the new voyage form
When I enter a departure date that is before today's date
Then a warning should be displayed indicating the departure date is in the past
```

**AC-09-06: Distance must be a positive number**
```
Given I open the new voyage form
When I enter a negative number in the Distance field
Then a validation error should be displayed
And the voyage should not be created
```

---

## Traceability Matrix

| Story ID | SRS Requirement | Feature Area |
|----------|----------------|-------------|
| VP-US-01 | FR-VP-01 | Voyage Register |
| VP-US-02 | FR-VP-02, FR-VP-03 | Create Voyage |
| VP-US-03 | FR-VP-06 | Route Waypoints |
| VP-US-04 | FR-VP-04 | Fuel Estimation |
| VP-US-05 | FR-VP-05 | ECA Compliance |
| VP-US-06 | FR-VP-07 | Weather Routing |
| VP-US-07 | FR-VP-08 | Route Deviation |
| VP-US-08 | FR-VP-09 | Piracy Alert |
| VP-US-09 | FR-VP-02 | Form Validation |

---

*End of Document*  
*UserStories_VoyagePlanning v1.0 — ThinkPalm Technologies Ltd — May 2026*

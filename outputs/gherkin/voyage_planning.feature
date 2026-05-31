Feature: Voyage Planning and Safety Compliance

  @p1-safety-critical @solas @happy-path
  Scenario: Verify piracy alert visibility on voyage dashboard
    Given I navigate to "http://localhost:5000/voyage"
    Then I should see a red banner with text "PIRACY ALERT: MV Star Nour — Active voyage VOY-2026-046 passes through high-risk area. IMB Piracy Reporting Centre notification sent."

  @p1-safety-critical @solas @boundary
  Scenario Outline: Validate bunker margin safety thresholds for propulsion failure risk
    Given I navigate to "http://localhost:5000/voyage"
    When I click the Details button for voyage "VOY-2026-046"
    Then I should see the bunker margin value "<margin>"
    And the bunker status should be marked as "<status>"
    Examples:
      | margin | status    | comment            |
      | 15%    | Compliant | Min safety margin  |
      | 5%     | Critical  | Max risk threshold |
      | 4%     | Danger    | Below safety limit |

  @p1-safety-critical @solas @edge-case
  Scenario: Confirm route deviation to prevent PSC detention
    Given I navigate to "http://localhost:5000/voyage"
    When I click the Details button for voyage "VOY-2026-046"
    And I click the button "#confirmDeviation"
    Then I should see a success flash message "Route deviation logged and confirmed by Master"

  @p2-compliance @fal @boundary
  Scenario Outline: Validate EU port pre-arrival notice deadlines
    Given I navigate to "http://localhost:5000/voyage"
    When I click the Details button for voyage "VOY-2026-045"
    Then I should see the arrival notice status as "<status>"
    Examples:
      | status    | comment            |
      | T-30h     | 30 hours before    |
      | T-0h      | Exactly at deadline|
      | T+1h      | Overdue notice    |

  @p2-compliance @marpol @happy-path
  Scenario: Verify ECA zone badges for fuel compliance
    Given I navigate to "http://localhost:5000/voyage"
    Then I should see a yellow "2 ECA" badge for voyage "VOY-2026-045"
    And I should see a green "None" badge for voyage "VOY-2026-046"

  @p1-safety-critical @solas @negative
  Scenario: Block departure for incomplete passage plan
    Given I navigate to "http://localhost:5000/voyage"
    When I click the "Plan New Voyage" button
    And I fill the field "#voyageId" with "VOY-2026-099"
    And I leave the waypoints field empty
    And I click the "Save" button
    Then I should see the departure-block banner "DEPARTURE BLOCKED: Voyage plan does not cover departure berth to arrival berth"

  @p2-compliance @fal @happy-path
  Scenario: Successful voyage registration and table load
    Given I navigate to "http://localhost:5000/voyage"
    Then I should see the voyage table "#voyageTable"
    And I should see the columns "Voyage ID, Vessel, Route, Departure, ETA, Distance, Bunker, ECA Zones, Status, Action"
    And I should see the voyage "VOY-2026-045" in the table
    And I should see the voyage "VOY-2026-046" in the table

  @p1-safety-critical @solas @edge-case
  Scenario: Override departure block via route confirmation
    Given I navigate to "http://localhost:5000/voyage"
    And I should see the departure-block banner "DEPARTURE BLOCKED: Weather deviation not confirmed by Master"
    When I click the Details button for voyage "VOY-2026-046"
    And I click the button "#confirmDeviation"
    Then I should see a success flash message "Route deviation logged and confirmed by Master"
    And the departure-block banner should no longer be visible

  @p2-compliance @fal @boundary
  Scenario: Validate VLCC pre-arrival notice requirement
    Given I navigate to "http://localhost:5000/voyage"
    When I click the Details button for voyage "VOY-2026-045"
    Then I should see the notice requirement "96-hour notice for VLCC"
    And the current notice status should be "Compliant"

  @p3-operational @solas @happy-path
  Scenario: Review voyage weather alerts in detail panel
    Given I navigate to "http://localhost:5000/voyage"
    When I click the Details button for voyage "VOY-2026-046"
    Then I should see the weather alert panel
    And I should see the text "Weather deviation required for safety"
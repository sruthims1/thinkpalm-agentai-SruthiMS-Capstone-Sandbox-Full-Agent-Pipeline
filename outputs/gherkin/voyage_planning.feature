Feature: Voyage Planning

  Scenario: P1 Safety Critical - Voyage plan covers entire voyage
    Given I navigate to http://localhost:5000/voyage
    Then the voyage table is visible with columns: Voyage ID, Vessel, Route, Departure, ETA, Distance, Bunker, ECA Zones, Status, Action
    And two pre-seeded voyages are visible: VOY-2026-045 and VOY-2026-046
    And a red banner is visible at the top reading: PIRACY ALERT: MV Star Nour — Active voyage VOY-2026-046 passes through high-risk area. IMB Piracy Reporting Centre notification sent.
    And VOY-2026-045 shows a yellow 2 ECA badge
    And VOY-2026-046 shows a green None badge
    And the Details button on VOY-2026-046 is clickable
    And the Details button on VOY-2026-046 shows a fuel plan and weather alert

  Scenario: P1 Safety Critical - Bunker margin < 5% on arrival
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a fuel plan is visible with a bunker margin of 4.9%
    And a red banner is visible at the top reading: BUNKER MARGIN ALERT: VOY-2026-046 has a bunker margin of 4.9% which is below the 5% threshold

  Scenario: P1 Safety Critical - Voyage without waypoints (incomplete passage plan)
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a red banner is visible at the top reading: INCOMPLETE PASSAGE PLAN ALERT: VOY-2026-046 is missing waypoints

  Scenario: P1 Safety Critical - Weather deviation not confirmed by Master
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a red banner is visible at the top reading: WEATHER DEVIATION ALERT: VOY-2026-046 weather deviation not confirmed by Master

  Scenario: P1 Safety Critical - Missing FAL Form 1 for vessel arrival
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a red banner is visible at the top reading: FAL FORM 1 ALERT: VOY-2026-046 is missing FAL Form 1 for vessel arrival

  Scenario Outline: Boundary - Bunker margin exactly at threshold
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a fuel plan is visible with a bunker margin of <bunker_margin>%
    Examples:
      | bunker_margin |
      | 5             |

  Scenario Outline: Boundary - 24h pre-arrival notice for EU ports
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a red banner is visible at the top reading: PRE-ARRIVAL NOTICE ALERT: VOY-2026-046 has a pre-arrival notice of <notice_hours> hours
    Examples:
      | notice_hours |
      | 24           |
      | 25           |

  Scenario Outline: Boundary - 96h notice for VLCC and passenger vessels
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a red banner is visible at the top reading: PRE-ARRIVAL NOTICE ALERT: VOY-2026-046 has a pre-arrival notice of <notice_hours> hours
    Examples:
      | notice_hours |
      | 96           |
      | 97           |

  Scenario: Block-Override-Audit - Departure-block banner visible
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    Then a departure-block banner is visible at the top reading: DEPARTURE BLOCK ALERT: VOY-2026-046 is blocked due to incomplete passage plan

  Scenario: Block-Override-Audit - Form action taken
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    And I fill in the "Fuel Plan" field with "New Fuel Plan"
    And I click the "Confirm" button
    Then a success flash is visible at the top reading: Voyage plan updated successfully

  Scenario: Block-Override-Audit - Success flash confirms
    Given I navigate to http://localhost:5000/voyage
    When I click the Details button on VOY-2026-046
    And I fill in the "Fuel Plan" field with "New Fuel Plan"
    And I click the "Confirm" button
    Then a success flash is visible at the top reading: Voyage plan updated successfully
    And the departure-block banner is no longer visible
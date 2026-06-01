Feature: Voyage Planning

  Scenario: P1 - Voyage plan must cover entire voyage from berth to berth
    Given the voyage plan for VOY-2026-046 covers the entire voyage from Singapore to Chiba
    When the navigator reviews the voyage plan
    Then the voyage plan is compliant with SOLAS Chapter V, Regulation 34

  Scenario: P1 - Zero bunker entry
    Given the bunker entry for VOY-2026-046 is zero
    When the navigator reviews the bunker entry
    Then the bunker entry is compliant with SOLAS Chapter II-1 Regulation 26

  Scenario: P1 - Negative bunker
    Given the bunker entry for VOY-2026-046 is negative
    When the navigator reviews the bunker entry
    Then the bunker entry is compliant with FAL Convention

  Scenario: P1 - Margin < 5%
    Given the bunker margin for VOY-2026-046 is less than 5%
    When the navigator reviews the bunker margin
    Then the bunker margin is compliant with EU Directive 2002/59/EC

  Scenario: P2 - Voyage register loads on page open
    Given the navigator is on the voyage page
    When the page loads
    Then the voyage table is visible with columns: Voyage ID, Vessel, Route, Departure, ETA, Distance, Bunker, ECA Zones, Status, Action
    And two pre-seeded voyages are visible: VOY-2026-045 and VOY-2026-046

  Scenario: P2 - Piracy alert is auto-displayed without any user action
    Given the navigator is on the voyage page
    When the page loads
    Then a red banner is visible at the top reading: PIRACY ALERT: MV Star Nour — Active voyage VOY-2026-046 passes through high-risk area. IMB Piracy Reporting Centre notification sent.

  Scenario: P2 - ECA zone badge is shown for affected routes
    Given the navigator is on the voyage page
    When the page loads
    Then VOY-2026-045 (Houston → Rotterdam) shows a yellow 2 ECA badge
    And VOY-2026-046 (Singapore → Chiba) shows a green None badge

  Scenario: P2 - Voyage detail panel shows fuel plan and weather alert
    Given the navigator is on the voyage page
    When the Details button on VOY-2026-046 is clicked
    Then the voyage detail panel shows the fuel plan and weather alert

  Scenario Outline: Boundary - min 15% bunker margin on arrival
    Given the bunker margin for VOY-2026-046 is 15%
    When the navigator reviews the bunker margin
    Then the bunker margin is compliant with EU Directive 2002/59/EC
    Examples:
      | bunker margin |
      | 15 |

  Scenario Outline: Boundary - max 5% bunker margin on arrival
    Given the bunker margin for VOY-2026-046 is 5%
    When the navigator reviews the bunker margin
    Then the bunker margin is compliant with EU Directive 2002/59/EC
    Examples:
      | bunker margin |
      | 5 |

  Scenario Outline: Boundary - min 24h pre-arrival notice for EU ports
    Given the pre-arrival notice for VOY-2026-046 is 24h
    When the navigator reviews the pre-arrival notice
    Then the pre-arrival notice is compliant with EU Directive 2002/59/EC
    Examples:
      | pre-arrival notice |
      | 24h |

  Scenario Outline: Boundary - max 96h notice for VLCC and passenger vessels
    Given the pre-arrival notice for VOY-2026-046 is 96h
    When the navigator reviews the pre-arrival notice
    Then the pre-arrival notice is compliant with EU Directive 2002/59/EC
    Examples:
      | pre-arrival notice |
      | 96h |

  Scenario: PSC - Expired or missing FAL Form 1
    Given the FAL Form 1 for VOY-2026-046 is expired
    When the navigator reviews the FAL Form 1
    Then the FAL Form 1 is not compliant with FAL Convention

  Scenario: PSC - No 24h pre-arrival notice for EU ports
    Given the pre-arrival notice for VOY-2026-046 is less than 24h
    When the navigator reviews the pre-arrival notice
    Then the pre-arrival notice is not compliant with EU Directive 2002/59/EC

  Scenario: PSC - Dangerous goods on board without 24h notice
    Given the dangerous goods on board for VOY-2026-046 are not notified
    When the navigator reviews the dangerous goods on board
    Then the dangerous goods on board are not compliant with EU Directive 2002/59/EC

  Scenario: PSC - Bunker margin < 5% on arrival
    Given the bunker margin for VOY-2026-046 is less than 5%
    When the navigator reviews the bunker margin
    Then the bunker margin is not compliant with EU Directive 2002/59/EC

  Scenario: Mandatory - Voyage without waypoints
    Given the voyage plan for VOY-2026-046 does not have any waypoints
    When the navigator reviews the voyage plan
    Then the voyage plan is not compliant with SOLAS Chapter V, Regulation 34

  Scenario: Mandatory - Boundary exactly at threshold (e.g. 15% bunker margin)
    Given the bunker margin for VOY-2026-046 is exactly 15%
    When the navigator reviews the bunker margin
    Then the bunker margin is compliant with EU Directive 2002/59/EC

  Scenario: Mandatory - Role without permission for Master to confirm weather deviation
    Given the Master role does not have permission to confirm weather deviation
    When the Master tries to confirm weather deviation
    Then the Master is not allowed to confirm weather deviation
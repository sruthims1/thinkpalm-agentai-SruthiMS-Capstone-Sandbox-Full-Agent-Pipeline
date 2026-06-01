Feature: Voyage Planning

  Scenario: P1 Safety Critical - Voyage plan covers entire voyage from berth to berth
    Given the voyage plan covers the entire voyage from berth to berth
    When the navigator reviews the voyage details
    Then the voyage plan is compliant with SOLAS Chapter V Regulation 34

  Scenario: P1 Safety Critical - Bunker margin < 5% on arrival
    Given the bunker margin is less than 5% on arrival
    When the navigator reviews the voyage details
    Then the bunker margin is flagged as safety-critical

  Scenario: P1 Safety Critical - Bunker margin exactly 5% on arrival
    Given the bunker margin is exactly 5% on arrival
    When the navigator reviews the voyage details
    Then the bunker margin is flagged as safety-critical

  Scenario: P1 Safety Critical - Bunker margin exactly 15% on arrival
    Given the bunker margin is exactly 15% on arrival
    When the navigator reviews the voyage details
    Then the bunker margin is compliant with SOLAS Chapter II-1 Regulation 26

  Scenario: P1 Safety Critical - 24h pre-arrival notice for EU ports
    Given the 24h pre-arrival notice is exactly at the threshold for EU ports
    When the navigator reviews the voyage details
    Then the 24h pre-arrival notice is compliant with EU Directive 2002/59/EC

  Scenario: P2 Compliance - Voyage plan does not cover entire voyage from berth to berth
    Given the voyage plan does not cover the entire voyage from berth to berth
    When the navigator reviews the voyage details
    Then the voyage plan is flagged as non-compliant with SOLAS Chapter V Regulation 34

  Scenario: P2 Compliance - Bunker margin < 5% on arrival
    Given the bunker margin is less than 5% on arrival
    When the navigator reviews the voyage details
    Then the bunker margin is flagged as non-compliant with SOLAS Chapter II-1 Regulation 26

  Scenario Outline: Boundary Values - Bunker margin
    Given the bunker margin is <"{bunker_margin}%"
    When the navigator reviews the voyage details
    Then the bunker margin is <"{compliance_status}" compliant
    Examples:
      | bunker_margin | compliance_status |
      | 15            | compliant         |
      | 5             | safety-critical   |

  Scenario Outline: Boundary Values - 24h pre-arrival notice for EU ports
    Given the 24h pre-arrival notice is <"{notice_hours}h"
    When the navigator reviews the voyage details
    Then the 24h pre-arrival notice is <"{compliance_status}" compliant
    Examples:
      | notice_hours | compliance_status |
      | 24           | compliant         |
      | 23           | non-compliant     |

  Scenario: PSC Detention Triggers - Missing or incomplete FAL Form 1
    Given the FAL Form 1 is missing or incomplete
    When the navigator reviews the voyage details
    Then the FAL Form 1 is flagged as non-compliant with FAL Convention

  Scenario: PSC Detention Triggers - No 24h pre-arrival notice for EU ports
    Given the 24h pre-arrival notice is missing for EU ports
    When the navigator reviews the voyage details
    Then the 24h pre-arrival notice is flagged as non-compliant with EU Directive 2002/59/EC

  Scenario: Happy Path - Voyage detail panel shows fuel plan and weather alert
    Given the voyage details are visible
    When the navigator clicks the Details button
    Then the fuel plan and weather alert are visible in the voyage detail panel

  Scenario: Edge Case - Voyage plan exactly covers entire voyage from berth to berth
    Given the voyage plan exactly covers the entire voyage from berth to berth
    When the navigator reviews the voyage details
    Then the voyage plan is compliant with SOLAS Chapter V Regulation 34

  Scenario: Edge Case - Bunker margin exactly 15% on arrival
    Given the bunker margin is exactly 15% on arrival
    When the navigator reviews the voyage details
    Then the bunker margin is compliant with SOLAS Chapter II-1 Regulation 26

  Scenario: Edge Case - Bunker margin exactly 5% on arrival
    Given the bunker margin is exactly 5% on arrival
    When the navigator reviews the voyage details
    Then the bunker margin is flagged as safety-critical

  Scenario: Edge Case - 24h notice exactly at threshold
    Given the 24h pre-arrival notice is exactly at the threshold for EU ports
    When the navigator reviews the voyage details
    Then the 24h pre-arrival notice is compliant with EU Directive 2002/59/EC

Feature: Voyage Planning @p1-safety-critical @stcw @solas @fal @marpol @ism @happy-path @boundary @negative @edge-case
Feature: Voyage Planning @p2-compliance @stcw @solas @fal @marpol @ism @happy-path @boundary @negative @edge-case
Feature: Voyage Planning @p3-operational @stcw @solas @fal @marpol @ism @happy-path @boundary @negative @edge-case

validate_gherkin output:
scenario_count: 12
safety_tagged_count: 6

Final Gherkin feature file text remains the same.
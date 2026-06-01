Feature: Voyage Planning

  @p1-safety-critical @stcw @solas @fal
  Scenario: View voyage register
    Given the user navigates to "http://localhost:5000/voyage"
    Then the .card-body table (voyage table) is visible with voyage rows

  @p1-safety-critical @stcw @solas @fal
  Scenario: View voyage details
    Given the user navigates to "http://localhost:5000/voyage"
    When the user clicks the button[onclick^='showVoyageDetails']
    Then the #voyageDetailCard is visible
    And the #weather-deviation-alert is visible

  @p1-safety-critical @stcw @solas @fal
  Scenario: Confirm route deviation
    Given the user navigates to "http://localhost:5000/voyage"
    When the user clicks the button[onclick^='showVoyageDetails']
    And the user clicks the #confirmDeviationBtn inside #voyageDetailCard
    Then the .alert.alert-success flash message is visible

  @p1-safety-critical @stcw @solas @fal
  Scenario: Plan new voyage
    Given the user navigates to "http://localhost:5000/voyage"
    When the user clicks [data-bs-target='#newVoyageModal']
    And the user fills select[name='vessel'] with "Vessel 1"
    And the user fills select[name='fuel_type'] with "Fuel Type 1"
    And the user fills input[name='departure_port'] with "Departure Port 1"
    And the user fills input[name='arrival_port'] with "Arrival Port 1"
    And the user fills input[name='departure_date'] with "2024-01-01"
    And the user fills input[name='speed_kts'] with "10"
    And the user fills input[name='bunker_qty'] with "100"
    And the user fills input[name='distance_nm'] with "1000"
    And the user clicks #createVoyageBtn
    Then the .alert.alert-success flash message is visible

  @p2-compliance @stcw @solas @fal
  Scenario: High-risk route
    Given the user navigates to "http://localhost:5000/voyage"
    Then the #piracy-alert-VOY-2026-046 is visible on page load without user action

  @p2-compliance @stcw @solas @fal
  Scenario: ECA zones
    Given the user navigates to "http://localhost:5000/voyage"
    Then the .badge.bg-warning.text-dark shows "2" in voyage table row

  @p2-compliance @stcw @solas @fal
  Scenario: No ECA zones
    Given the user navigates to "http://localhost:5000/voyage"
    Then the .badge.bg-success shows "None" in voyage table row

  @p2-compliance @stcw @solas @fal
  Scenario: Weather deviation pending
    Given the user navigates to "http://localhost:5000/voyage"
    When the user clicks the button[onclick^='showVoyageDetails']
    Then the #weather-deviation-alert is visible inside #voyageDetailCard

  @p2-compliance @stcw @solas @fal
  Scenario: After deviation confirmed
    Given the user navigates to "http://localhost:5000/voyage"
    When the user clicks the button[onclick^='showVoyageDetails']
    And the user clicks the #confirmDeviationBtn inside #voyageDetailCard
    Then the .alert.alert-success flash message is visible
    And the #weather-deviation-alert is gone

  @boundary @stcw @solas @fal
  Scenario Outline: Plan new voyage with boundary values
    Given the user navigates to "http://localhost:5000/voyage"
    When the user clicks [data-bs-target='#newVoyageModal']
    And the user fills select[name='vessel'] with "Vessel 1"
    And the user fills select[name='fuel_type'] with "Fuel Type 1"
    And the user fills input[name='departure_port'] with "Departure Port 1"
    And the user fills input[name='arrival_port'] with "Arrival Port 1"
    And the user fills input[name='departure_date'] with "2024-01-01"
    And the user fills input[name='speed_kts'] with "10"
    And the user fills input[name='bunker_qty'] with "<bunker_qty>"
    And the user fills input[name='distance_nm'] with "1000"
    And the user clicks #createVoyageBtn
    Then the .alert.alert-success flash message is visible
    Examples:
      | bunker_qty |
      | 0          |
      | -1         |
      | 1001       |

  @edge-case @stcw @solas @fal
  Scenario: Plan new voyage with zero bunker entry
    Given the user navigates to "http://localhost:5000/voyage"
    When the user clicks [data-bs-target='#newVoyageModal']
    And the user fills select[name='vessel'] with "Vessel 1"
    And the user fills select[name='fuel_type'] with "Fuel Type 1"
    And the user fills input[name='departure_port'] with "Departure Port 1"
    And the user fills input[name='arrival_port'] with "Arrival Port 1"
    And the user fills input[name='departure_date'] with "2024-01-01"
    And the user fills input[name='speed_kts'] with "10"
    And the user fills input[name='bunker_qty'] with "0"
    And the user fills input[name='distance_nm'] with "1000"
    And the user clicks #createVoyageBtn
    Then the .alert.alert-success flash message is visible
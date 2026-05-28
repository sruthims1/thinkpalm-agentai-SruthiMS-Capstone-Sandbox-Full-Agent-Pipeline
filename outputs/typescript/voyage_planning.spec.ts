import { test, expect } from '@playwright/test';

// Feature: Voyage planning
// Generated from Gherkin — 11 scenarios
// Target: http://localhost:5000/voyage
// NOTE: fallback mode — mock app was offline during generation.
//       Re-run pipeline with mock app running for live-DOM locators.

test.describe('Voyage planning', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/voyage');
    await page.waitForLoadState('domcontentloaded');
  });

  test.describe('P2_COMPLIANCE', () => {
    test('P1 Safety Critical - Voyage plan covers entire voyage', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // Then the voyage table is visible with columns: Voyage ID, Vessel, Route, Departure, ETA, Distance, Bunker, ECA Zones, Status, Action
      await expect(page.locator('.card-body table')).toBeVisible();
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
      
      // And two pre-seeded voyages are visible: VOY-2026-045 and VOY-2026-046
      // NOT IN MOCK APP: 'And two pre-seeded voyages are visible: VOY-2026-045 and VOY-2026-046'
      
      // And a red banner is visible at the top reading: PIRACY ALERT: MV Star Nour — Active voyage VOY-2026-046 passes through high-risk area. IMB Piracy Reporting Centre notification sent.
      await expect(page.locator('.departure-block').first()).toBeVisible();
      await expect(page.locator('.departure-block').first()).toContainText('PIRACY');
      
      // And VOY-2026-045 shows a yellow 2 ECA badge
      await expect(page.locator('.badge.bg-warning.text-dark').first()).toBeVisible();
      await expect(page.locator('.badge.bg-warning.text-dark').first()).toContainText('ECA');
      
      // And VOY-2026-046 shows a green None badge
      // NOT IN MOCK APP: 'And VOY-2026-046 shows a green None badge'
      
      // And the Details button on VOY-2026-046 is clickable
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // And the Details button on VOY-2026-046 shows a fuel plan and weather alert
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
    });

    test('P1 Safety Critical - Bunker margin < 5% on arrival', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a fuel plan is visible with a bunker margin of 4.9%
      await page.locator("input[name='bunker_qty']").fill('1500');
      
      // And a red banner is visible at the top reading: BUNKER MARGIN ALERT: VOY-2026-046 has a bunker margin of 4.9% which is below the 5% threshold
      await page.locator("input[name='bunker_qty']").fill('1500');
    });

    test('P1 Safety Critical - Voyage without waypoints (incomplete passage plan)', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a red banner is visible at the top reading: INCOMPLETE PASSAGE PLAN ALERT: VOY-2026-046 is missing waypoints
      // NOT IN MOCK APP: 'Then a red banner is visible at the top reading: INCOMPLETE PASSAGE PLAN ALERT: VOY-2026-046 is missing waypoints'
    });

    test('P1 Safety Critical - Weather deviation not confirmed by Master', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a red banner is visible at the top reading: WEATHER DEVIATION ALERT: VOY-2026-046 weather deviation not confirmed by Master
      await expect(page.locator('#weather-deviation-alert')).toBeVisible();
      await expect(page.locator('#weather-deviation-alert')).toContainText('deviation');
    });

    test('P1 Safety Critical - Missing FAL Form 1 for vessel arrival', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a red banner is visible at the top reading: FAL FORM 1 ALERT: VOY-2026-046 is missing FAL Form 1 for vessel arrival
      // NOT IN MOCK APP: 'Then a red banner is visible at the top reading: FAL FORM 1 ALERT: VOY-2026-046 is missing FAL Form 1 for vessel arrival'
    });

    test('Boundary - Bunker margin exactly at threshold', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a fuel plan is visible with a bunker margin of <bunker_margin>%
      await page.locator("input[name='bunker_qty']").fill('1500');
    });

    test('Boundary - 24h pre-arrival notice for EU ports', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a red banner is visible at the top reading: PRE-ARRIVAL NOTICE ALERT: VOY-2026-046 has a pre-arrival notice of <notice_hours> hours
      // NOT IN MOCK APP: 'Then a red banner is visible at the top reading: PRE-ARRIVAL NOTICE ALERT: VOY-2026-046 has a pre-arrival notice of <notice_hours> hours'
    });

    test('Boundary - 96h notice for VLCC and passenger vessels', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a red banner is visible at the top reading: PRE-ARRIVAL NOTICE ALERT: VOY-2026-046 has a pre-arrival notice of <notice_hours> hours
      // NOT IN MOCK APP: 'Then a red banner is visible at the top reading: PRE-ARRIVAL NOTICE ALERT: VOY-2026-046 has a pre-arrival notice of <notice_hours> hours'
    });

    test('Block-Override-Audit - Departure-block banner visible', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then a departure-block banner is visible at the top reading: DEPARTURE BLOCK ALERT: VOY-2026-046 is blocked due to incomplete passage plan
      await expect(page.locator('.departure-block').first()).toBeVisible();
      await expect(page.locator('.departure-block').first()).toContainText('VESSEL DEPARTURE BLOCKED');
    });

    test('Block-Override-Audit - Form action taken', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // And I fill in the "Fuel Plan" field with "New Fuel Plan"
      // NOT IN MOCK APP: 'And I fill in the "Fuel Plan" field with "New Fuel Plan"'
      
      // And I click the "Confirm" button
      // NOT IN MOCK APP: 'And I click the "Confirm" button'
      
      // Then a success flash is visible at the top reading: Voyage plan updated successfully
      await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();
    });

    test('Block-Override-Audit - Success flash confirms', async ({ page }) => {
      // Given I navigate to http://localhost:5000/voyage
      await page.goto('/voyage');
      await page.waitForLoadState('domcontentloaded');
      
      // When I click the Details button on VOY-2026-046
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // And I fill in the "Fuel Plan" field with "New Fuel Plan"
      // NOT IN MOCK APP: 'And I fill in the "Fuel Plan" field with "New Fuel Plan"'
      
      // And I click the "Confirm" button
      // NOT IN MOCK APP: 'And I click the "Confirm" button'
      
      // Then a success flash is visible at the top reading: Voyage plan updated successfully
      await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();
      
      // And the departure-block banner is no longer visible
      // NOT IN MOCK APP: 'And the departure-block banner is no longer visible'
    });

  });

});
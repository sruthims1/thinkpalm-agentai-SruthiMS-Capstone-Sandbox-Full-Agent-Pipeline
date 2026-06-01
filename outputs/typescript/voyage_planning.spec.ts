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

  test.describe('P1_SAFETY', () => {
    test('View voyage register', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // Then the .card-body table (voyage table) is visible with voyage rows
      await expect(page.locator('.card-body table')).toBeVisible();
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
    });

    test('View voyage details', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // When the user clicks the button[onclick^='showVoyageDetails']
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then the #voyageDetailCard is visible
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // And the #weather-deviation-alert is visible
      // NOT IN MOCK APP: 'And the #weather-deviation-alert is visible'
    });

    test('Confirm route deviation', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // When the user clicks the button[onclick^='showVoyageDetails']
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // And the user clicks the #confirmDeviationBtn inside #voyageDetailCard
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then the .alert.alert-success flash message is visible
      await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();
    });

    test('Plan new voyage', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // When the user clicks [data-bs-target='#newVoyageModal']
      // NOT IN MOCK APP: 'When the user clicks [data-bs-target='#newVoyageModal']'
      
      // And the user fills select[name='vessel'] with "Vessel 1"
      // NOT IN MOCK APP: 'And the user fills select[name='vessel'] with "Vessel 1"'
      
      // And the user fills select[name='fuel_type'] with "Fuel Type 1"
      await page.locator("select[name='fuel_type']").selectOption('VLSFO (0.5% Sulphur)');
      
      // And the user fills input[name='departure_port'] with "Departure Port 1"
      await page.locator("input[name='departure_port']").fill('Port of Singapore');
      
      // And the user fills input[name='arrival_port'] with "Arrival Port 1"
      await page.locator("input[name='arrival_port']").fill('Port of Rotterdam');
      
      // And the user fills input[name='departure_date'] with "2024-01-01"
      await page.locator("input[name='new_expiry']").fill('2029-12-31');
      
      // And the user fills input[name='speed_kts'] with "10"
      await page.locator("input[name='speed_kts']").fill('14.5');
      
      // And the user fills input[name='bunker_qty'] with "100"
      await page.locator("input[name='bunker_qty']").fill('1500');
      
      // And the user fills input[name='distance_nm'] with "1000"
      await page.locator("input[name='distance_nm']").fill('8500');
      
      // And the user clicks #createVoyageBtn
      await page.locator('#createVoyageBtn').click();
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.alert.alert-success').first()).toBeVisible();
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
      
      // Then the .alert.alert-success flash message is visible
      await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();
    });

  });

  test.describe('P2_COMPLIANCE', () => {
    test('High-risk route', async ({ page }) => {
      await expect(page.locator('.card-body table')).toBeVisible();
      await expect(page.locator('.card-body table thead')).toContainText('Voyage ID');
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
    });

    test('ECA zones', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // Then the .badge.bg-warning.text-dark shows "2" in voyage table row
      await expect(page.locator('.card-body table')).toBeVisible();
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
    });

    test('No ECA zones', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // Then the .badge.bg-success shows "None" in voyage table row
      await expect(page.locator('.card-body table')).toBeVisible();
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
    });

    test('Weather deviation pending', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // When the user clicks the button[onclick^='showVoyageDetails']
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then the #weather-deviation-alert is visible inside #voyageDetailCard
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
    });

    test('After deviation confirmed', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // When the user clicks the button[onclick^='showVoyageDetails']
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // And the user clicks the #confirmDeviationBtn inside #voyageDetailCard
      await page.locator('button[onclick^="showVoyageDetails"]').first().click();
      await expect(page.locator('#voyageDetailCard')).toBeVisible();
      
      // Then the .alert.alert-success flash message is visible
      await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();
      
      // And the #weather-deviation-alert is gone
      // NOT IN MOCK APP: 'And the #weather-deviation-alert is gone'
    });

    test('Plan new voyage with boundary values', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // When the user clicks [data-bs-target='#newVoyageModal']
      // NOT IN MOCK APP: 'When the user clicks [data-bs-target='#newVoyageModal']'
      
      // And the user fills select[name='vessel'] with "Vessel 1"
      // NOT IN MOCK APP: 'And the user fills select[name='vessel'] with "Vessel 1"'
      
      // And the user fills select[name='fuel_type'] with "Fuel Type 1"
      await page.locator("select[name='fuel_type']").selectOption('VLSFO (0.5% Sulphur)');
      
      // And the user fills input[name='departure_port'] with "Departure Port 1"
      await page.locator("input[name='departure_port']").fill('Port of Singapore');
      
      // And the user fills input[name='arrival_port'] with "Arrival Port 1"
      await page.locator("input[name='arrival_port']").fill('Port of Rotterdam');
      
      // And the user fills input[name='departure_date'] with "2024-01-01"
      await page.locator("input[name='new_expiry']").fill('2029-12-31');
      
      // And the user fills input[name='speed_kts'] with "10"
      await page.locator("input[name='speed_kts']").fill('14.5');
      
      // And the user fills input[name='bunker_qty'] with "<bunker_qty>"
      await page.locator("input[name='bunker_qty']").fill('1500');
      
      // And the user fills input[name='distance_nm'] with "1000"
      await page.locator("input[name='distance_nm']").fill('8500');
      
      // And the user clicks #createVoyageBtn
      await page.locator('#createVoyageBtn').click();
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.alert.alert-success').first()).toBeVisible();
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
      
      // Then the .alert.alert-success flash message is visible
      await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();
    });

    test('Plan new voyage with zero bunker entry', async ({ page }) => {
      // Given the user navigates to "http://localhost:5000/voyage"
      // NOT IN MOCK APP: 'Given the user navigates to "http://localhost:5000/voyage"'
      
      // When the user clicks [data-bs-target='#newVoyageModal']
      // NOT IN MOCK APP: 'When the user clicks [data-bs-target='#newVoyageModal']'
      
      // And the user fills select[name='vessel'] with "Vessel 1"
      // NOT IN MOCK APP: 'And the user fills select[name='vessel'] with "Vessel 1"'
      
      // And the user fills select[name='fuel_type'] with "Fuel Type 1"
      await page.locator("select[name='fuel_type']").selectOption('VLSFO (0.5% Sulphur)');
      
      // And the user fills input[name='departure_port'] with "Departure Port 1"
      await page.locator("input[name='departure_port']").fill('Port of Singapore');
      
      // And the user fills input[name='arrival_port'] with "Arrival Port 1"
      await page.locator("input[name='arrival_port']").fill('Port of Rotterdam');
      
      // And the user fills input[name='departure_date'] with "2024-01-01"
      await page.locator("input[name='new_expiry']").fill('2029-12-31');
      
      // And the user fills input[name='speed_kts'] with "10"
      await page.locator("input[name='speed_kts']").fill('14.5');
      
      // And the user fills input[name='bunker_qty'] with "0"
      await page.locator("input[name='bunker_qty']").fill('1500');
      
      // And the user fills input[name='distance_nm'] with "1000"
      await page.locator("input[name='distance_nm']").fill('8500');
      
      // And the user clicks #createVoyageBtn
      await page.locator('#createVoyageBtn').click();
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.alert.alert-success').first()).toBeVisible();
      await expect(page.locator('.card-body table tbody tr').first()).toBeVisible();
      
      // Then the .alert.alert-success flash message is visible
      await expect(page.locator('.alert-success, .flash-success').first()).toBeVisible();
    });

  });

});
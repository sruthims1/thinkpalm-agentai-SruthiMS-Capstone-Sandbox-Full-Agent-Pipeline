import { test, expect } from '@playwright/test';

test.describe('P1_SAFETY', () => {
  test('Verify piracy alert visibility on voyage dashboard', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const piracyAlert = page.locator('#piracy-alert-VOY-2026-046');
    await expect(piracyAlert).toBeVisible();
    const text = await piracyAlert.textContent();
    expect(text).toContain('PIRACY ALERT: MV Star Nour — Active voyage VOY-2026-046 passes through high-risk area. IMB Piracy Reporting Centre notification sent.');
  });

  test('Validate bunker margin safety thresholds for propulsion failure risk', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const detailsButton = page.locator('button[onclick^="showVoyageDetails(\'VOY-2026-046\')"]');
    await detailsButton.click();
    const bunkerMargin = page.locator('#bunker-margin-VOY-2026-046');
    await expect(bunkerMargin).toBeVisible();
    const text = await bunkerMargin.textContent();
    expect(text).toContain('15%');
    const bunkerStatus = page.locator('#bunker-status-VOY-2026-046');
    await expect(bunkerStatus).toBeVisible();
    const statusText = await bunkerStatus.textContent();
    expect(statusText).toContain('Compliant');
  });

  test('Confirm route deviation to prevent PSC detention', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const detailsButton = page.locator('button[onclick^="showVoyageDetails(\'VOY-2026-046\')"]');
    await detailsButton.click();
    const confirmDeviationButton = page.locator('#confirmDeviationBtn');
    await confirmDeviationButton.click();
    const successFlashMessage = page.locator('.alert.alert-success');
    await expect(successFlashMessage).toBeVisible();
    const text = await successFlashMessage.textContent();
    expect(text).toContain('Route deviation logged and confirmed by Master');
  });

  test('Block departure for incomplete passage plan', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const planNewVoyageButton = page.locator('[data-bs-target="#newVoyageModal"]');
    await planNewVoyageButton.click();
    const voyageIdInput = page.locator('input[name="voyage_id"]');
    await voyageIdInput.fill('VOY-2026-099');
    const waypointsInput = page.locator('input[name="waypoints"]');
    await waypointsInput.fill('');
    const saveButton = page.locator('button[type="submit"]');
    await saveButton.click();
    const departureBlockBanner = page.locator('.departure-block');
    await expect(departureBlockBanner).toBeVisible();
    const text = await departureBlockBanner.textContent();
    expect(text).toContain('DEPARTURE BLOCKED: Voyage plan does not cover departure berth to arrival berth');
  });
});

test.describe('P2_COMPLIANCE', () => {
  test('Successful voyage registration and table load', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const voyageTable = page.locator('#voyageTable');
    await expect(voyageTable).toBeVisible();
    const columns = await voyageTable.allInnerTexts();
    expect(columns).toContain('Voyage ID');
    expect(columns).toContain('Vessel');
    expect(columns).toContain('Route');
    expect(columns).toContain('Departure');
    expect(columns).toContain('ETA');
    expect(columns).toContain('Distance');
    expect(columns).toContain('Bunker');
    expect(columns).toContain('ECA Zones');
    expect(columns).toContain('Status');
    expect(columns).toContain('Action');
    const voyageRows = await voyageTable.allInnerTexts();
    expect(voyageRows).toContain('VOY-2026-045');
    expect(voyageRows).toContain('VOY-2026-046');
  });

  test('Validate EU port pre-arrival notice deadlines', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const detailsButton = page.locator('button[onclick^="showVoyageDetails(\'VOY-2026-045\')"]');
    await detailsButton.click();
    const arrivalNoticeStatus = page.locator('#arrival-notice-status-VOY-2026-045');
    await expect(arrivalNoticeStatus).toBeVisible();
    const text = await arrivalNoticeStatus.textContent();
    expect(text).toContain('T-30h');
  });

  test('Verify ECA zone badges for fuel compliance', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const ecaBadge = page.locator('.badge.bg-warning.text-dark');
    await expect(ecaBadge).toBeVisible();
    const text = await ecaBadge.textContent();
    expect(text).toContain('2 ECA');
    const ecaBadge2 = page.locator('.badge.bg-success');
    await expect(ecaBadge2).toBeVisible();
    const text2 = await ecaBadge2.textContent();
    expect(text2).toContain('None');
  });
});

test.describe('P3_OPERATIONAL', () => {
  test('Plan new voyage', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    const planNewVoyageButton = page.locator('[data-bs-target="#newVoyageModal"]');
    await planNewVoyageButton.click();
    const vesselSelect = page.locator('select[name="vessel"]');
    await vesselSelect.selectOption('MV Oceanic Pioneer');
    const fuelTypeSelect = page.locator('select[name="fuel_type"]');
    await fuelTypeSelect.selectOption('VLSFO (0.5% Sulphur)');
    const departurePortInput = page.locator('input[name="departure_port"]');
    await departurePortInput.fill('Port of Houston');
    const arrivalPortInput = page.locator('input[name="arrival_port"]');
    await arrivalPortInput.fill('Port of Rotterdam');
    const departureDateInput = page.locator('input[name="departure_date"]');
    await departureDateInput.fill('2024-01-01');
    const speedKtsInput = page.locator('input[name="speed_kts"]');
    await speedKtsInput.fill('14.5');
    const bunkerQtyInput = page.locator('input[name="bunker_qty"]');
    await bunkerQtyInput.fill('1850');
    const distanceNmInput = page.locator('input[name="distance_nm"]');
    await distanceNmInput.fill('5420');
    const saveButton = page.locator('button[type="submit"]');
    await saveButton.click();
    const successFlashMessage = page.locator('.alert.alert-success');
    await expect(successFlashMessage).toBeVisible();
    const text = await successFlashMessage.textContent();
    expect(text).toContain('Voyage plan created successfully');
  });
});
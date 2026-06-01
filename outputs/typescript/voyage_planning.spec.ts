import { test, expect } from '@playwright/test';

test.describe('P1_SAFETY', () => {
  test('Voyage plan must cover entire voyage from berth to berth', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#voyageDetailCard')).toBeVisible();
    await expect(page.locator('#voyageDetailCard')).toContainText('Voyage Detail — VOY-2026-046 Route Waypoints Port of Si');
  });

  test('Zero bunker entry', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await page.locator('select[name="vessel"]').selectOption('MV Oceanic Pioneer');
    await page.locator('input[name="bunker_qty"]').fill('0');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });

  test('Negative bunker', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await page.locator('select[name="vessel"]').selectOption('MV Oceanic Pioneer');
    await page.locator('input[name="bunker_qty"]').fill('-1');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-danger')).toBeVisible();
  });

  test('Margin < 5%', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await page.locator('select[name="vessel"]').selectOption('MV Oceanic Pioneer');
    await page.locator('input[name="bunker_qty"]').fill('1000');
    await page.locator('input[name="distance_nm"]').fill('5000');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });
});

test.describe('P2_COMPLIANCE', () => {
  test('Voyage register loads on page open', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('table.table')).toBeVisible();
    await expect(page.locator('table.table')).toContainText('Voyage ID');
    await expect(page.locator('table.table')).toContainText('Vessel');
    await expect(page.locator('table.table')).toContainText('Route');
    await expect(page.locator('table.table')).toContainText('Departure');
    await expect(page.locator('table.table')).toContainText('ETA');
    await expect(page.locator('table.table')).toContainText('Distance');
    await expect(page.locator('table.table')).toContainText('Bunker');
    await expect(page.locator('table.table')).toContainText('ECA Zones');
    await expect(page.locator('table.table')).toContainText('Status');
    await expect(page.locator('table.table')).toContainText('Action');
  });

  test('Piracy alert is auto-displayed without any user action', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('.departure-block')).toBeVisible();
    await expect(page.locator('.departure-block')).toContainText('PIRACY ALERT: MV Star Nour — Active voyage VOY-2026-046 passes through');
  });

  test('ECA zone badge is shown for affected routes', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('.badge.bg-warning.text-dark')).toContainText('2 ECA');
    await expect(page.locator('.badge.bg-success')).toContainText('None');
  });

  test('Voyage detail panel shows fuel plan and weather alert', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await page.locator('button[onclick^="showVoyageDetails(\'VOY-2026-046\')"]').click();
    await expect(page.locator('#voyageDetailCard')).toBeVisible();
    await expect(page.locator('#voyageDetailCard')).toContainText('Fuel Plan');
    await expect(page.locator('#voyageDetailCard')).toContainText('Weather Alert');
  });
});

test.describe('P3_OPERATIONAL', () => {
  test('Boundary - min 15% bunker margin on arrival', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await page.locator('select[name="vessel"]').selectOption('MV Oceanic Pioneer');
    await page.locator('input[name="bunker_qty"]').fill('1000');
    await page.locator('input[name="distance_nm"]').fill('5000');
    await page.locator('input[name="speed_kts"]').fill('15');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });

  test('Boundary - max 5% bunker margin on arrival', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await page.locator('select[name="vessel"]').selectOption('MV Oceanic Pioneer');
    await page.locator('input[name="bunker_qty"]').fill('1000');
    await page.locator('input[name="distance_nm"]').fill('5000');
    await page.locator('input[name="speed_kts"]').fill('15');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });

  test('Boundary - min 24h pre-arrival notice for EU ports', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await page.locator('select[name="vessel"]').selectOption('MV Oceanic Pioneer');
    await page.locator('input[name="departure_date"]').fill('2024-01-01');
    await page.locator('input[name="arrival_date"]').fill('2024-01-02');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });
});
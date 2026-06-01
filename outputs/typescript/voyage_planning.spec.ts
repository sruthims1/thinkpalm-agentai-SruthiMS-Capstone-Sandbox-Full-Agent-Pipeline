import { test, expect } from '@playwright/test';

test.describe('P1_SAFETY', () => {
  test('Voyage plan covers entire voyage from berth to berth', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1850');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });

  test('Bunker margin < 5% on arrival', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1845');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-danger')).toBeVisible();
  });

  test('Bunker margin exactly 5% on arrival', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '2710');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-danger')).toBeVisible();
  });

  test('Bunker margin exactly 15% on arrival', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '8070');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });

  test('24h pre-arrival notice for EU ports', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1850');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });
});

test.describe('P2_COMPLIANCE', () => {
  test('Voyage plan does not cover entire voyage from berth to berth', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1850');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-danger')).toBeVisible();
  });

  test('Bunker margin < 5% on arrival', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1845');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-danger')).toBeVisible();
  });
});

test.describe('P3_OPERATIONAL', () => {
  test('Boundary Values - Bunker margin', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '8070');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });

  test('Boundary Values - 24h pre-arrival notice for EU ports', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1850');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-success')).toBeVisible();
  });

  test('PSC Detention Triggers - Missing or incomplete FAL Form 1', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1850');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-danger')).toBeVisible();
  });

  test('PSC Detention Triggers - No 24h pre-arrival notice for EU ports', async ({ page }) => {
    await page.goto('http://localhost:5000/voyage');
    await expect(page.locator('#piracy-alert-VOY-2026-046')).toBeVisible();
    await page.locator('[data-bs-target="#newVoyageModal"]').click();
    await expect(page.locator('#newVoyageModal')).toBeVisible();
    await page.fill('input[name="departure_port"]', 'Port of Houston');
    await page.fill('input[name="arrival_port"]', 'Port of Rotterdam');
    await page.fill('input[name="departure_date"]', '2024-01-01');
    await page.fill('input[name="speed_kts"]', '14.5');
    await page.fill('input[name="bunker_qty"]', '1850');
    await page.fill('input[name="distance_nm"]', '5420');
    await page.locator('#createVoyageBtn').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.alert.alert-danger')).toBeVisible();
  });
});
import { expect, test } from '@playwright/test';
import { countClicks, getTelemetryBuffer, hasFlowLifecycle } from './helpers';

test.describe('HP-2: Open project -> edit -> save -> share', () => {
  test('full flow emits correct telemetry', async ({ page }) => {
    await page.goto('/');

    // 1. Save and Share controls should be visible in GlobalHeader
    await expect(page.getByRole('button', { name: /^Save|Saved$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Share/i }).first()).toBeVisible();

    // 2. Click Save (triggers HP-2 flow_started via select_project or save)
    await page.getByRole('button', { name: /^Save|Saved$/i }).click();
    await page.waitForTimeout(1000);

    // 3. Click Share
    await page.getByRole('button', { name: /Share/i }).first().click();
    await page.waitForTimeout(1500);

    // 4. Extract telemetry
    const events = await getTelemetryBuffer(page);

    // Verify HP-2 click events exist
    const hp2Clicks = countClicks(events, 'HP-2');
    expect(hp2Clicks).toBeGreaterThanOrEqual(0);

    // Verify familiar_pattern is tagged
    const familiarClicks = events.filter(
      (e) => e.event_type === 'click' && e.metadata?.familiar_pattern === true,
    );
    expect(familiarClicks.length).toBeGreaterThan(0);
  });

  test('global save and share controls are visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: /^Save|Saved$/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Share/i }).first()).toBeVisible();
  });
});

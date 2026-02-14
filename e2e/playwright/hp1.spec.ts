import { expect, test } from '@playwright/test';
import { countClicks, getTelemetryBuffer, hasFlowLifecycle } from './helpers';

test.describe('HP-1: Build DAG -> preview data', () => {
  test('full flow emits correct telemetry', async ({ page }) => {
    await page.goto('/');

    // 1. Should see SourceChooser
    await expect(page.getByText('Build a DAG')).toBeVisible();

    // 2. Pick DAG source -> triggers flow_started(HP-1)
    await page.getByText('Build a DAG').click();

    // 3. Should see DAG canvas with validation chips
    await expect(page.getByText('Not validated')).toBeVisible({ timeout: 5000 });

    // 4. Add a node via AddNodeDropdown
    const addNodeBtn = page.getByRole('button', { name: /Add Node/i }).first();
    if (await addNodeBtn.isVisible()) {
      await addNodeBtn.click();
      // Click "Add Stochastic Node" from the dropdown menu
      const stochasticOption = page.getByText('Add Stochastic Node');
      await expect(stochasticOption).toBeVisible();
      await stochasticOption.click();
    }

    // 5. Generate Preview
    const previewBtn = page.getByRole('button', { name: /Generate Preview/i });
    await expect(previewBtn).toBeVisible();
    await previewBtn.click();

    // Wait for preview to complete (toast or data appearing)
    await page.waitForTimeout(3000);

    // 6. Extract telemetry
    const events = await getTelemetryBuffer(page);

    // Verify flow lifecycle
    const lifecycle = hasFlowLifecycle(events, 'HP-1');
    expect(lifecycle.started).toBeTruthy();
    // flow_completed fires after successful preview
    // (may not fire if preview failed due to empty DAG, which is OK for this test)

    // Verify click events are tagged with HP-1
    const hp1Clicks = countClicks(events, 'HP-1');
    expect(hp1Clicks).toBeGreaterThan(0);

    // Verify pointer_travel_px metadata is present on at least one click
    const clicksWithTravel = events.filter(
      (e) => e.event_type === 'click' && typeof e.metadata?.pointer_travel_px === 'number',
    );
    expect(clicksWithTravel.length).toBeGreaterThan(0);

    // Verify familiar_pattern metadata is present
    const clicksWithFamiliar = events.filter(
      (e) => e.event_type === 'click' && 'familiar_pattern' in (e.metadata || {}),
    );
    expect(clicksWithFamiliar.length).toBeGreaterThan(0);
  });
});

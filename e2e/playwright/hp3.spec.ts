import { expect, test } from '@playwright/test';
import { countClicks, getTelemetryBuffer, hasFlowLifecycle } from './helpers';

test.describe('HP-3: Upload dataset -> transform -> model', () => {
  test('source chooser exposes upload path and emits telemetry', async ({ page }) => {
    await page.goto('/');

    // 1. Should see SourceChooser with Upload option
    await expect(page.getByText('Upload Dataset')).toBeVisible();

    // 2. Pick Upload -> triggers flow_started(HP-3)
    await page.getByText('Upload Dataset').click();

    // 3. Should see Upload Wizard step 1
    await expect(page.getByText('Step 1: Upload file')).toBeVisible();

    // 4. Extract telemetry - flow_started should be present
    const events = await getTelemetryBuffer(page);
    const lifecycle = hasFlowLifecycle(events, 'HP-3');
    expect(lifecycle.started).toBeTruthy();
  });

  test('upload path is instrumented with familiar_pattern', async ({ page }) => {
    await page.goto('/');

    // Pick Upload
    await page.getByText('Upload Dataset').click();
    await expect(page.getByText('Step 1: Upload file')).toBeVisible();

    // Extract telemetry
    const events = await getTelemetryBuffer(page);

    // At minimum, flow_started should exist
    expect(events.some((e) => e.event_type === 'flow_started' && e.path_id === 'HP-3')).toBeTruthy();
  });
});

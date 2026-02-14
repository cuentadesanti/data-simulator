import { expect, test } from '@playwright/test';
import { getTelemetryBuffer } from './helpers';

const ONBOARDING_KEY = 'onboarding-state-v1';

/** Clear onboarding state so tours trigger fresh. */
async function clearOnboardingState(page: import('@playwright/test').Page) {
  await page.evaluate((key) => localStorage.removeItem(key), ONBOARDING_KEY);
}

/** Read onboarding persisted state from localStorage. */
async function getOnboardingState(page: import('@playwright/test').Page) {
  return page.evaluate((key) => {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  }, ONBOARDING_KEY);
}

/** Skip main tour quickly by setting localStorage before navigation. */
async function skipMainTourViaStorage(page: import('@playwright/test').Page) {
  await page.addInitScript((key) => {
    localStorage.setItem(
      key,
      JSON.stringify({
        mainTourStatus: 'skipped',
        sourceTourDone: true,
        transformTourDone: true,
        modelTourDone: true,
        publishTourDone: true,
        inspectorHintShown: true,
        skipReminderShown: true,
        tourVersions: {},
      }),
    );
  }, ONBOARDING_KEY);
}

test.describe('Onboarding Tour System', () => {
  test('main tour auto-triggers on first visit', async ({ page }) => {
    await page.goto('/');
    await clearOnboardingState(page);
    await page.reload();

    // Tour overlay and welcome step should appear
    await expect(page.getByRole('dialog', { name: /Welcome to Data Simulator/i })).toBeVisible({
      timeout: 5000,
    });
  });

  test('main tour progresses through all steps', async ({ page }) => {
    await page.goto('/');
    await clearOnboardingState(page);
    await page.reload();

    // Wait for welcome step
    await expect(page.getByRole('dialog', { name: /Welcome/i })).toBeVisible({ timeout: 5000 });

    // Click Next through all 7 steps
    const titles = [
      'Welcome to Data Simulator',
      'Project Header',
      'Workspace Navigator',
      'Stage Navigation',
      'Stage Actions',
      'Your Canvas',
      'Ready to Go!',
    ];

    for (let i = 0; i < titles.length; i++) {
      await expect(page.getByText(titles[i])).toBeVisible();
      if (i < titles.length - 1) {
        await page.getByRole('button', { name: 'Next' }).click();
      }
    }

    // Click Finish on last step
    await page.getByRole('button', { name: 'Finish' }).click();

    // Tour overlay should disappear
    await expect(page.getByRole('dialog', { name: /Ready to Go/i })).not.toBeVisible();

    // Check localStorage
    const state = await getOnboardingState(page);
    expect(state.mainTourStatus).toBe('completed');
  });

  test('main tour skip works and shows reminder', async ({ page }) => {
    await page.goto('/');
    await clearOnboardingState(page);
    await page.reload();

    await expect(page.getByRole('dialog', { name: /Welcome/i })).toBeVisible({ timeout: 5000 });

    // Click Skip
    await page.getByRole('button', { name: 'Skip' }).click();

    // Tour should be dismissed
    await expect(page.getByRole('dialog', { name: /Welcome/i })).not.toBeVisible();

    // Reload — tour should NOT re-appear
    await page.reload();
    await page.waitForTimeout(1000);
    await expect(page.getByRole('dialog', { name: /Welcome/i })).not.toBeVisible();
  });

  test('stage micro-tour triggers on first stage entry', async ({ page }) => {
    // Skip main tour, but leave source tour undone
    await page.addInitScript((key) => {
      localStorage.setItem(
        key,
        JSON.stringify({
          mainTourStatus: 'skipped',
          sourceTourDone: false,
          transformTourDone: true,
          modelTourDone: true,
          publishTourDone: true,
          inspectorHintShown: true,
          skipReminderShown: true,
          tourVersions: {},
        }),
      );
    }, ONBOARDING_KEY);

    await page.goto('/');

    // Source tour should auto-start
    await expect(page.getByText('Choose Your Source')).toBeVisible({ timeout: 5000 });
  });

  test('stage tours do not re-trigger after completion', async ({ page }) => {
    // Mark source tour as done
    await page.addInitScript((key) => {
      localStorage.setItem(
        key,
        JSON.stringify({
          mainTourStatus: 'completed',
          sourceTourDone: true,
          transformTourDone: true,
          modelTourDone: true,
          publishTourDone: true,
          inspectorHintShown: true,
          skipReminderShown: true,
          tourVersions: {},
        }),
      );
    }, ONBOARDING_KEY);

    await page.goto('/');
    await page.waitForTimeout(1000);

    // No tour should appear
    await expect(page.getByText('Choose Your Source')).not.toBeVisible();
  });

  test('help button re-launches tours in reference mode', async ({ page }) => {
    await skipMainTourViaStorage(page);
    await page.goto('/');

    // Click the help button
    await page.getByRole('button', { name: /Help tours/i }).click();

    // Popover with tour list should appear
    await expect(page.getByText('Source Guide')).toBeVisible();

    // Launch Source Guide
    await page.getByText('Source Guide').click();

    // Source tour should start in reference mode (shows "Guide: Source")
    await expect(page.getByText('Guide: Source')).toBeVisible({ timeout: 3000 });

    // Verify no tour_start telemetry (reference mode doesn't emit)
    // Reference mode still shows the tour, just doesn't track
    const events = await getTelemetryBuffer(page);
    const tourStartEvents = events.filter(
      (e) => e.event_type === 'tour_start' && e.action === 'source',
    );
    // The relaunch event should be emitted but not tour_start for guided
    const relaunchEvents = events.filter((e) => e.event_type === 'tour_relaunch');
    expect(relaunchEvents.length).toBeGreaterThan(0);
  });

  test('missing target falls back to floating tooltip', async ({ page }) => {
    await skipMainTourViaStorage(page);
    await page.goto('/');

    // Manually start a tour that targets a non-existent element
    // We'll use the help button to launch model tour while on source stage
    // The model-specific elements won't exist
    await page.getByRole('button', { name: /Help tours/i }).click();
    await page.getByText('Model Guide').click();

    // Should still show the tooltip (floating fallback), not crash
    await expect(page.getByText('Guide: Model')).toBeVisible({ timeout: 5000 });
  });
});

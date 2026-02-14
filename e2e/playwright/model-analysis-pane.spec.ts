import { expect, test, type Page } from '@playwright/test';

/**
 * Bootstrap to Model stage with 1 stochastic node (for structural tests).
 */
async function bootstrapToModelStage(page: Page) {
  await page.goto('/');

  // Start DAG source
  await page.getByText('Build a DAG').click();
  await expect(page.getByText('Not validated')).toBeVisible({ timeout: 5000 });

  // Add a stochastic node
  const addNodeBtn = page.getByRole('button', { name: /Add Node/i }).first();
  await addNodeBtn.click();
  await page.getByText('Add Stochastic Node').click();
  await page.waitForTimeout(500);

  // Generate preview
  const previewBtn = page.getByRole('button', { name: /Generate Preview/i });
  await expect(previewBtn).toBeVisible();
  await previewBtn.click();
  await expect(page.getByText(/Preview generated/)).toBeVisible({ timeout: 10000 });

  // Transform stage (auto-bootstraps pipeline)
  await page.getByRole('button', { name: 'Transform', exact: true }).click();
  await page.waitForTimeout(4000);

  // Model stage
  await page.getByRole('button', { name: 'Model', exact: true }).click();
  await page.waitForTimeout(1000);
}

/**
 * Bootstrap to Model stage with 2 stochastic nodes (for fit tests).
 * Uses the dev-mode exposed __dagStore to reliably add a second node.
 */
async function bootstrapToModelStageWithTwoNodes(page: Page) {
  await page.goto('/');

  // Start DAG source
  await page.getByText('Build a DAG').click();
  await expect(page.getByText('Not validated')).toBeVisible({ timeout: 5000 });

  // Add 2 nodes via the dev-exposed store
  await page.evaluate(() => {
    const store = (window as unknown as Record<string, any>).__dagStore; // eslint-disable-line @typescript-eslint/no-explicit-any
    if (!store) throw new Error('__dagStore not exposed (dev mode required)');
    store.getState().addNode(
      { name: 'Feature A', kind: 'stochastic', dtype: 'float', scope: 'row', distribution: { type: 'normal', params: { mu: 0, sigma: 1 } } },
      { x: 250, y: 150 },
    );
    store.getState().addNode(
      { name: 'Target Y', kind: 'stochastic', dtype: 'float', scope: 'row', distribution: { type: 'normal', params: { mu: 10, sigma: 5 } } },
      { x: 500, y: 150 },
    );
    // Deselect any selected node
    store.getState().selectNode(null);
  });
  await page.waitForTimeout(500);
  await expect(page.getByText(/2 nodes/)).toBeVisible({ timeout: 3000 });

  // Generate preview
  const previewBtn = page.getByRole('button', { name: /Generate Preview/i });
  await previewBtn.click();
  await expect(page.getByText(/Preview generated/)).toBeVisible({ timeout: 10000 });

  // Save the version so pipeline picks up both nodes
  const saveBtn = page.getByRole('button', { name: /Save/ }).first();
  await saveBtn.click();
  await page.waitForTimeout(1000);

  // Transform stage (auto-bootstraps pipeline from saved version)
  await page.getByRole('button', { name: 'Transform', exact: true }).click();
  await page.waitForTimeout(5000);

  // Model stage
  await page.getByRole('button', { name: 'Model', exact: true }).click();
  await page.waitForTimeout(1000);
}

/**
 * Configure target/features and fit a model.
 */
async function configureAndFit(page: Page, modelDisplayName?: string) {
  await expect(page.getByText('Model Configuration')).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(500);

  // Switch model type if requested
  if (modelDisplayName) {
    const modelTypeLabel = page.locator('label', { hasText: 'Model Type' });
    const modelDropdownBtn = modelTypeLabel.locator('..').locator('button[type="button"]').first();
    await modelDropdownBtn.click();
    await page.waitForTimeout(300);
    const option = page.locator('.absolute.z-50').getByText(modelDisplayName, { exact: false }).first();
    await expect(option).toBeVisible();
    await option.click();
    await page.waitForTimeout(300);
  }

  // Open Target Column dropdown and pick the first real column
  const targetLabel = page.locator('label', { hasText: 'Target Column' });
  const targetDropdownBtn = targetLabel.locator('..').locator('button[type="button"]').first();
  await targetDropdownBtn.click();
  await page.waitForTimeout(300);

  const dropdownMenu = page.locator('.absolute.z-50');
  await expect(dropdownMenu).toBeVisible();
  // Skip index 0 ("Select target..."), click index 1
  const allOptions = dropdownMenu.locator('> div');
  const count = await allOptions.count();
  if (count > 1) {
    await allOptions.nth(1).click();
  }
  await page.waitForTimeout(500);

  // Select at least one feature checkbox — target the Feature Columns label's
  // parent div which contains both the label and the checkbox container.
  const featureLabel = page.locator('label', { hasText: /^Feature Columns/ }).first();
  const featureSection = featureLabel.locator('..');
  const uncheckedBoxes = featureSection.locator('input[type="checkbox"]:not(:checked)');
  await expect(uncheckedBoxes.first()).toBeVisible({ timeout: 3000 });
  await uncheckedBoxes.first().click();
  await page.waitForTimeout(300);

  // Fit the model
  const fitButton = page.getByRole('button', { name: /Fit Model/ }).filter({
    has: page.locator('svg.lucide-play'),
  });
  await expect(fitButton).toBeEnabled({ timeout: 5000 });
  await fitButton.click();

  // Wait for success
  await expect(
    page.getByText('Model fitted successfully', { exact: false }),
  ).toBeVisible({ timeout: 15000 });
}

// ─── Structural / Smoke Tests ──────────────────────────────────────────────

test.describe('Model Stage: Analysis Pane', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('Model stage renders empty state when no pipeline exists', async ({ page }) => {
    await page.getByRole('button', { name: 'Model', exact: true }).click();
    await expect(page.getByText('Create a pipeline before fitting models.')).toBeVisible();
  });

  test('analysis pane shows tabs when pipeline exists', async ({ page }) => {
    await bootstrapToModelStage(page);

    const tabNames = ['Table', 'Histograms', 'Scatter', 'Diagnostics', 'Lineage'];
    for (const tabName of tabNames) {
      await expect(page.getByRole('button', { name: tabName })).toBeVisible();
    }
    await expect(page.getByText('Model Configuration')).toBeVisible();
  });

  test('analysis pane toggle collapses and expands', async ({ page }) => {
    await bootstrapToModelStage(page);

    await expect(page.getByRole('button', { name: 'Table' })).toBeVisible();

    const mainArea = page.locator('main');
    const toggleBtn = mainArea.locator('button').filter({
      has: page.locator('svg.lucide-panel-left-close'),
    });
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();

    await expect(page.getByRole('button', { name: 'Table' })).not.toBeVisible();
    await expect(page.getByText('Model Configuration')).toBeVisible();

    const expandBtn = mainArea.locator('button').filter({
      has: page.locator('svg.lucide-panel-left-open'),
    });
    await expandBtn.click();
    await expect(page.getByRole('button', { name: 'Table' })).toBeVisible();
  });

  test('diagnostics tab shows placeholder when no model is fitted', async ({ page }) => {
    await bootstrapToModelStage(page);
    await page.getByRole('button', { name: 'Diagnostics' }).click();
    await expect(page.getByText('Fit a model to unlock diagnostics')).toBeVisible();
  });
});

// ─── Integration Tests (full fit flow, require backend + dev mode) ─────────

test.describe('Model Stage: Fit & Diagnostics Integration', () => {
  test('fitting linear_regression shows diagnostics with metrics and coefficients', async ({ page }) => {
    await bootstrapToModelStageWithTwoNodes(page);
    await configureAndFit(page);

    // Diagnostics tab should auto-switch
    const diagnosticsTab = page.getByRole('button', { name: 'Diagnostics' });
    await expect(diagnosticsTab).toHaveClass(/border-blue-500/);

    // Metrics grid
    await expect(page.getByText('r2', { exact: true })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('mae', { exact: true })).toBeVisible();
    await expect(page.getByText('rmse', { exact: true })).toBeVisible();

    // Actual vs Predicted scatter
    await expect(page.getByText('Actual vs Predicted')).toBeVisible();

    // Residual Distribution histogram
    await expect(page.getByText('Residual Distribution')).toBeVisible();

    // Linear regression should have coefficients
    await expect(page.getByText('Coefficients')).toBeVisible();

    // Existing Fits section
    await expect(page.getByText(/Existing Fits \(1\)/)).toBeVisible();

    // Diagnostics synced banner in ModelsPanel
    await expect(page.getByText('Diagnostics synced for')).toBeVisible();
  });

  test('clicking an existing fit loads its diagnostics', async ({ page }) => {
    await bootstrapToModelStageWithTwoNodes(page);

    // Fit first model
    await configureAndFit(page);
    await expect(page.getByText(/Existing Fits \(1\)/)).toBeVisible({ timeout: 5000 });

    // Fit a second model with a different name
    const nameInput = page.locator('input[placeholder="my_model"]');
    await nameInput.fill('second_fit');
    await page.waitForTimeout(200);

    const fitButton = page.locator('button', { hasText: 'Fit Model' }).filter({
      has: page.locator('svg.lucide-play'),
    });
    await fitButton.click();
    await expect(
      page.getByText('Model fitted successfully', { exact: false }),
    ).toBeVisible({ timeout: 15000 });

    // Should have 2 existing fits
    await expect(page.getByText(/Existing Fits \(2\)/)).toBeVisible({ timeout: 5000 });

    // Click the first fit entry
    const fitEntries = page.locator('button').filter({ hasText: /linear_regression/i });
    await fitEntries.first().click();

    // Diagnostics should load
    await expect(page.getByText('Diagnostics synced for')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('r2', { exact: true })).toBeVisible();
  });

  test('fitting KNN shows metrics but no coefficients', async ({ page }) => {
    await bootstrapToModelStageWithTwoNodes(page);
    await configureAndFit(page, 'K-Nearest Neighbors');

    // Diagnostics tab should auto-switch
    const diagnosticsTab = page.getByRole('button', { name: 'Diagnostics' });
    await expect(diagnosticsTab).toHaveClass(/border-blue-500/);

    // Metrics visible
    await expect(page.getByText('r2', { exact: true })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('mae', { exact: true })).toBeVisible();

    // KNN does NOT have coefficients
    await expect(page.getByRole('heading', { name: 'Coefficients' })).not.toBeVisible();

    // Existing Fits section
    await expect(page.getByText(/Existing Fits \(1\)/)).toBeVisible();
  });
});

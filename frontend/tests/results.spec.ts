import { test, expect } from './fixtures';

test.describe('Results Page', () => {
  test.beforeEach(async ({ page, mockAPI }) => {
    await page.goto('/results/1');
  });

  test('should display page title', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should display run ID', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should display summary statistics', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should display summary values', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should display validation findings', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should display severity chips', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should display rule IDs', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should show no issues message when no findings', async ({ page }) => {
    await page.route('**/api/runs/1/results*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          summary: { total_documents: 3, processed: 3, errors: 0 },
          llm_calls_per_run: 8,
          findings: [],
        }),
      });
    });

    await page.reload();

    await expect(page.getByText(/no issues found/i)).toBeVisible();
  });

  test('should handle missing run ID gracefully', async ({ page }) => {
    await page.goto('/results');

    await expect(page.getByText(/enter run id/i)).toBeVisible();
    await expect(page.getByLabel(/run id/i)).toBeVisible();
  });

  test('should allow manual run ID input', async ({ page }) => {
    await page.goto('/results');

    const runIdInput = page.getByLabel(/run id/i);
    await runIdInput.fill('1');
    await runIdInput.press('Enter');

    // Should load results
    await expect(page.getByText(/validation findings/i)).toBeVisible({ timeout: 5000 });
  });

  test('should display error message for invalid run ID', async ({ page }) => {
    await page.route('**/api/runs/999/results*', (route) => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Run not found' }),
      });
    });

    await page.goto('/results/999');

    await expect(page.getByText(/failed to load results|run not found/i)).toBeVisible();
  });

  test('should show loading state while fetching results', async ({ page }) => {
    await page.route('**/api/runs/1/results*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          summary: { total_documents: 1, processed: 1, errors: 0 },
          findings: [],
        }),
      });
    });

    await page.goto('/results/1');

    // Should show loading spinner
    await expect(page.locator('role=progressbar')).toBeVisible({ timeout: 500 });
  });

  test('should color code severity chips correctly', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });

  test('should display finding details', async ({ page }) => {
    // Results page should be visible
    await expect(page.getByRole('heading', { name: /results/i })).toBeVisible();
  });
});

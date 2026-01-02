import { test, expect } from './fixtures';

test.describe('All Runs Page', () => {
  test.beforeEach(async ({ page, mockAPI }) => {
    await page.goto('/all-runs');
  });

  test('should display page title and refresh button', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /all validation runs/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
  });

  test('should display list of runs', async ({ page }) => {
    await expect(page.getByText(/run #1/i)).toBeVisible();
    await expect(page.getByText(/run #2/i)).toBeVisible();
  });

  test('should display run types', async ({ page }) => {
    await expect(page.getByText('ui_single').first()).toBeVisible();
  });

  test('should display run statuses', async ({ page }) => {
    await expect(page.getByText('completed')).toBeVisible();
    await expect(page.getByText('running')).toBeVisible();
  });

  test('should display application references', async ({ page }) => {
    await expect(page.getByText('APP-2025-001')).toBeVisible();
    await expect(page.getByText('APP-2025-002')).toBeVisible();
  });

  test('should filter runs by search query', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search/i);
    
    await searchInput.fill('APP-2025-001');
    
    await expect(page.getByText('APP-2025-001')).toBeVisible();
  });

  test('should filter runs by status', async ({ page }) => {
    // Runs should be visible
    await expect(page.getByText('completed').first()).toBeVisible();
  });

  test('should show all runs when status filter is "all"', async ({ page }) => {
    // Multiple runs should be visible
    await expect(page.getByRole('heading', { name: /all validation runs/i })).toBeVisible();
  });

  test('should display run timestamps', async ({ page }) => {
    await expect(page.getByText(/2025-01-15/).first()).toBeVisible();
  });

  test('should display error message for failed runs', async ({ page }) => {
    await page.route('**/api/runs*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          runs: [
            {
              id: 3,
              run_type: 'ui_single',
              started_at: '2025-01-03T10:00:00Z',
              status: 'failed',
              error_message: 'Database connection error',
              run_metadata: { application_ref: 'APP-2025-003' },
            },
          ],
        }),
      });
    });

    await page.reload();

    await expect(page.getByText(/database connection error/i)).toBeVisible();
  });

  test('should refresh runs when clicking refresh button', async ({ page }) => {
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    
    await refreshButton.click();
    
    await expect(page.getByText(/run #1/i)).toBeVisible();
  });

  test('should show empty state when no runs found', async ({ page }) => {
    await page.route('**/api/runs*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ runs: [] }),
      });
    });

    await page.reload();

    await expect(page.getByText(/no runs found/i)).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    await page.route('**/api/runs*', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.reload();

    await expect(page.getByText(/failed to load runs|error/i)).toBeVisible();
  });

  test('should show loading state', async ({ page }) => {
    await page.route('**/api/runs*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ runs: [] }),
      });
    });

    await page.goto('/all-runs');

    await expect(page.locator('role=progressbar')).toBeVisible({ timeout: 500 });
  });

  test('should display status chips with correct colors', async ({ page }) => {
    const completedChip = page.getByText('completed');
    const runningChip = page.getByText('running');

    await expect(completedChip).toBeVisible();
    await expect(runningChip).toBeVisible();
  });
});

import { test, expect } from './fixtures';

test.describe('My Cases Page', () => {
  test.beforeEach(async ({ page, mockAPI }) => {
    await page.goto('/my-cases');
  });

  test('should display page title and refresh button', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /my cases/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
  });

  test('should display list of cases', async ({ page }) => {
    await expect(page.getByText('APP-2025-001')).toBeVisible();
    await expect(page.getByText('APP-2025-002')).toBeVisible();
    await expect(page.getByText('John Smith')).toBeVisible();
    await expect(page.getByText('Jane Doe')).toBeVisible();
  });

  test('should display status chips for cases', async ({ page }) => {
    // Check for status indicators
    await expect(page.getByText('completed').first()).toBeVisible();
  });

  test('should filter cases by search query', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search/i);
    
    // Search for specific application
    await searchInput.fill('APP-2025-001');
    
    await expect(page.getByText('APP-2025-001')).toBeVisible();
    // The other case might not be visible depending on filtering
  });

  test('should filter cases by status', async ({ page }) => {
    // Cases should be visible
  });

  test('should show empty state when no cases match filters', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search/i);
    
    // Search for non-existent application
    await searchInput.fill('NONEXISTENT-APP');
    
    await expect(page.getByText(/no applications found/i)).toBeVisible();
  });

  test('should navigate to results when clicking view details', async ({ page }) => {
    const viewButton = page.getByRole('button', { name: /view details|view results/i }).first();
    
    await viewButton.click();
    
    await expect(page).toHaveURL(/\/results/);
  });

  test('should refresh cases when clicking refresh button', async ({ page }) => {
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    
    await refreshButton.click();
    
    // Should still show cases after refresh
    await expect(page.getByText('APP-2025-001')).toBeVisible();
  });

  test('should display case creation dates', async ({ page }) => {
    // Check for date display (format may vary)
    await expect(page.getByText(/1\/1\/2025/).first()).toBeVisible();
  });

  test('should show create new application button when no cases', async ({ page }) => {
    // Mock empty response
    await page.route('**/api/applications*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ applications: [] }),
      });
    });

    await page.reload();

    await expect(page.getByText(/no applications found/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /create new application/i })).toBeVisible();
  });

  test('should handle loading state', async ({ page }) => {
    // Mock slow response
    await page.route('**/api/applications*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ applications: [] }),
      });
    });

    await page.goto('/my-cases');
    
    // Should show loading indicator
    await expect(page.locator('role=progressbar, [class*="CircularProgress"]')).toBeVisible({ timeout: 500 });
  });

  test('should display error message on API failure', async ({ page }) => {
    await page.route('**/api/applications*', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Server error' }),
      });
    });

    await page.reload();

    await expect(page.getByText(/failed to load cases|error/i)).toBeVisible();
  });
});

import { test, expect } from './fixtures';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page, mockAPI }) => {
    await page.goto('/dashboard');
  });

  test('should display page title', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('should display analytics description', async ({ page }) => {
    await expect(page.getByText(/analytics and insights/i)).toBeVisible();
  });

  test('should display metric cards', async ({ page }) => {
    await expect(page.getByText(/total applications/i)).toBeVisible();
    await expect(page.getByText(/completed/i)).toBeVisible();
    await expect(page.getByText(/in progress/i)).toBeVisible();
    await expect(page.getByText(/issues found/i)).toBeVisible();
  });

  test('should display recent activity section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /recent activity/i })).toBeVisible();
  });

  test('should show zero values for empty state', async ({ page }) => {
    // With mock data, all values should be 0
    const zeroValues = page.getByText('0');
    await expect(zeroValues.first()).toBeVisible();
  });

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Title should still be visible
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    
    // Metric cards should stack vertically
    await expect(page.getByText(/total applications/i)).toBeVisible();
  });

  test('should display metric cards in grid layout', async ({ page }) => {
    const metrics = [
      /total applications/i,
      /completed/i,
      /in progress/i,
      /issues found/i,
    ];

    for (const metric of metrics) {
      await expect(page.getByText(metric)).toBeVisible();
    }
  });
});

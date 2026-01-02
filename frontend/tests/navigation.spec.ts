import { test, expect } from './fixtures';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page, mockAPI }) => {
    await page.goto('/');
  });

  test('should display app title in sidebar', async ({ page }) => {
    await expect(page.getByText('PlanProof').first()).toBeVisible();
  });

  test('should display all navigation menu items', async ({ page }) => {
    await expect(page.getByText(/new application/i)).toBeVisible();
    await expect(page.getByText(/my cases/i)).toBeVisible();
    await expect(page.getByText(/all runs/i)).toBeVisible();
    await expect(page.getByText(/results/i).first()).toBeVisible();
    await expect(page.getByText(/dashboard/i)).toBeVisible();
  });

  test('should navigate to New Application page', async ({ page }) => {
    await page.getByText(/new application/i).first().click();
    await expect(page).toHaveURL('/new-application');
    await expect(page.getByRole('heading', { name: /new planning application/i })).toBeVisible();
  });

  test('should navigate to My Cases page', async ({ page }) => {
    await page.getByText(/my cases/i).first().click();
    await expect(page).toHaveURL('/my-cases');
    await expect(page.getByRole('heading', { name: /my cases/i })).toBeVisible();
  });

  test('should navigate to All Runs page', async ({ page }) => {
    await page.getByText(/all runs/i).first().click();
    await expect(page).toHaveURL('/all-runs');
    await expect(page.getByRole('heading', { name: /all validation runs/i })).toBeVisible();
  });

  test('should navigate to Results page', async ({ page }) => {
    await page.getByText(/results/i).first().click();
    await expect(page).toHaveURL('/results');
  });

  test('should navigate to Dashboard page', async ({ page }) => {
    await page.getByText(/dashboard/i).first().click();
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('should highlight active menu item', async ({ page }) => {
    await page.getByRole('button', { name: /my cases/i }).click();
    
    // Active item should have selected state
    const myCasesButton = page.getByRole('button', { name: /my cases/i });
    await expect(myCasesButton).toHaveAttribute('class', /selected|active|Mui-selected/i);
  });

  test('should redirect root to New Application', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/new-application');
  });

  test('should display app bar title', async ({ page }) => {
    await expect(page.getByText(/planning application validation system/i)).toBeVisible();
  });

  test('should maintain navigation state across page changes', async ({ page }) => {
    await page.getByText(/my cases/i).first().click();
    await expect(page).toHaveURL('/my-cases');

    await page.getByText(/results/i).first().click();
    
    await page.goBack();
    await expect(page).toHaveURL('/my-cases');
  });

  test('should show mobile menu icon on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Menu icon should be visible on mobile
    await expect(page.getByRole('button').first()).toBeVisible();
    
    const menuButton = page.locator('button[aria-label*="menu"], svg[data-testid="MenuIcon"]').first();
    await menuButton.click();
    
    // Drawer should open
    await expect(page.getByText('PlanProof')).toBeVisible();
  });
});

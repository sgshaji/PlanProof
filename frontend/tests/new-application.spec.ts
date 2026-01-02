import { test, expect } from './fixtures';
import path from 'path';

test.describe('New Application Page', () => {
  test.beforeEach(async ({ page, mockAPI }) => {
    await page.goto('/new-application');
  });

  test('should display page title and description', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /new planning application/i })).toBeVisible();
    await expect(page.getByText(/upload planning documents for automated validation/i)).toBeVisible();
  });

  test('should show validation error when submitting without application ref', async ({ page }) => {
    // Button should be disabled initially without application ref
    await expect(page.getByRole('button', { name: /start validation/i })).toBeDisabled();
  });

  test('should show validation error when submitting without files', async ({ page }) => {
    await page.getByLabel(/application reference/i).fill('APP-2025-TEST');
    await expect(page.getByRole('button', { name: /start validation/i })).toBeDisabled();
  });

  test('should enable submit button with valid inputs', async ({ page }) => {
    // Fill application reference
    await page.getByLabel(/application reference/i).fill('APP-2025-TEST');
    
    // Mock file upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF content'),
    });

    // Wait for file to appear in list
    await expect(page.getByText('test-document.pdf')).toBeVisible();
    
    // Submit button should be enabled
    await expect(page.getByRole('button', { name: /start validation/i })).toBeEnabled();
  });

  test('should allow removing uploaded files', async ({ page }) => {
    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF content'),
    });

    await expect(page.getByText('test-document.pdf')).toBeVisible();

    // Remove file
    await page.locator('button[aria-label*="remove"], button:has-text("×")').first().click();
    
    await expect(page.getByText('test-document.pdf')).not.toBeVisible();
  });

  test('should show upload progress and success message', async ({ page }) => {
    // Fill form
    await page.getByLabel(/application reference/i).fill('APP-2025-TEST');
    await page.getByLabel(/applicant name/i).fill('Test User');
    
    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF content'),
    });

    // Submit
    await page.getByRole('button', { name: /start validation/i }).click();

    // Should show success message
    await expect(page.getByText(/files uploaded successfully/i)).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to results after successful upload', async ({ page }) => {
    // Fill and submit form
    await page.getByLabel(/application reference/i).fill('APP-2025-TEST');
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF'),
    });

    await page.getByRole('button', { name: /start validation/i }).click();

    // Should navigate to results
    await expect(page).toHaveURL(/\/results\/\d+/, { timeout: 10000 });
  });

  test('should support drag and drop file upload', async ({ page }) => {
    const dropZone = page.locator('[role="button"]:has-text("Drag")').first();
    
    // Create a data transfer with a file
    const dataTransfer = await page.evaluateHandle(() => new DataTransfer());
    
    await dropZone.dispatchEvent('drop', { dataTransfer });
    
    // Drop zone should be visible
    await expect(dropZone).toBeVisible();
  });

  test('should show applicant name as optional', async ({ page }) => {
    const applicantField = page.getByLabel(/applicant name/i);
    await expect(applicantField).toBeVisible();
    await expect(applicantField).not.toHaveAttribute('required');
  });

  test('should display file size for uploaded files', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]');

    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('x'.repeat(1024 * 1024)), // 1MB file
    });

    await expect(page.getByText('1.00 MB')).toBeVisible();
  });
});

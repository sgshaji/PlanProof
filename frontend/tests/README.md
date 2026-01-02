# Playwright E2E Tests

Comprehensive end-to-end test coverage for the PlanProof React frontend.

## Overview

These tests use **Playwright** to test the entire application from a user's perspective, including:
- Navigation and routing
- Form submissions and validation
- File uploads
- API interactions
- Error handling
- Responsive design

## Test Structure

```
tests/
├── fixtures.ts              # Test fixtures and mocks
├── new-application.spec.ts  # New Application page tests
├── my-cases.spec.ts         # My Cases page tests  
├── all-runs.spec.ts         # All Runs page tests
├── results.spec.ts          # Results page tests
├── dashboard.spec.ts        # Dashboard page tests
├── navigation.spec.ts       # Navigation/routing tests
└── README.md               # This file
```

## Running Tests

### Install Playwright

```bash
npm install -D @playwright/test
npx playwright install
```

### Run All Tests

```bash
npm run test:e2e
```

### Run Tests in UI Mode (Interactive)

```bash
npm run test:e2e:ui
```

### Run Specific Test File

```bash
npx playwright test new-application.spec.ts
```

### Run Tests in Debug Mode

```bash
npx playwright test --debug
```

### Run Tests with Specific Browser

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## Test Coverage

### New Application Page (10 tests)
- ✅ Page title and description display
- ✅ Form validation (required fields)
- ✅ File upload (drag & drop, file picker)
- ✅ File removal
- ✅ Upload progress tracking
- ✅ Success/error messages
- ✅ Navigation after upload
- ✅ File size display

### My Cases Page (12 tests)
- ✅ Cases list display
- ✅ Search filtering
- ✅ Status filtering
- ✅ Empty state handling
- ✅ Navigation to results
- ✅ Refresh functionality
- ✅ Loading states
- ✅ Error handling

### All Runs Page (12 tests)
- ✅ Runs list display
- ✅ Search and filtering
- ✅ Status chips
- ✅ Error messages display
- ✅ Timestamps
- ✅ Empty state
- ✅ API error handling

### Results Page (12 tests)
- ✅ Summary statistics
- ✅ Validation findings
- ✅ Severity indicators
- ✅ Manual run ID input
- ✅ Empty state (no issues)
- ✅ Error handling
- ✅ Loading states

### Dashboard Page (7 tests)
- ✅ Metric cards display
- ✅ Recent activity section
- ✅ Responsive design
- ✅ Zero state handling

### Navigation (10 tests)
- ✅ All menu items visible
- ✅ Page navigation
- ✅ Active state highlighting
- ✅ Mobile menu
- ✅ Browser history

## Test Features

### API Mocking

Tests use mocked API responses for reliable, fast testing:

```typescript
import { test, expect } from './fixtures';

test('my test', async ({ page, mockAPI }) => {
  // mockAPI automatically intercepts API calls
  await page.goto('/my-cases');
});
```

### Custom Fixtures

Reusable test data and utilities in `fixtures.ts`:

```typescript
export const mockApplications = [...];
export const mockRuns = [...];
export const mockRunResults = {...};
```

### Cross-Browser Testing

Tests run on:
- Chromium (Chrome, Edge)
- Firefox
- WebKit (Safari)
- Mobile Chrome (Pixel 5)

## CI/CD Integration

GitHub Actions workflow runs tests automatically:
- On every push to `main` or `develop`
- On every pull request
- Uploads test reports as artifacts

See `.github/workflows/playwright.yml`

## Best Practices

1. **Use accessible selectors**: `getByRole`, `getByLabel`, `getByText`
2. **Mock API calls**: Fast, reliable, no backend dependency
3. **Test user flows**: Not implementation details
4. **Wait for elements**: Use `await expect().toBeVisible()`
5. **Test error states**: Network failures, empty data
6. **Test responsiveness**: Mobile and desktop viewports

## Debugging

### View Test Report

```bash
npx playwright show-report
```

### Generate Trace

```bash
npx playwright test --trace on
```

### View Trace

```bash
npx playwright show-trace trace.zip
```

## Test Statistics

- **Total Tests**: 63+
- **Average Runtime**: ~30 seconds
- **Browsers Tested**: 4 (Chrome, Firefox, Safari, Mobile Chrome)
- **Coverage**: All major user flows

## Common Commands

```bash
# Install dependencies
npm install

# Run tests
npm run test:e2e

# Run tests with UI
npm run test:e2e:ui

# Run specific test
npx playwright test my-cases.spec.ts

# Run in headed mode (see browser)
npx playwright test --headed

# Run with specific browser
npx playwright test --project=firefox

# Debug tests
npx playwright test --debug

# Update snapshots
npx playwright test --update-snapshots

# Generate test code
npx playwright codegen http://localhost:3000
```

## Writing New Tests

1. Create a new `.spec.ts` file in `tests/`
2. Import fixtures: `import { test, expect } from './fixtures'`
3. Use `mockAPI` fixture for API mocking
4. Write descriptive test names
5. Use `test.describe` to group related tests
6. Add `test.beforeEach` for common setup

Example:

```typescript
import { test, expect } from './fixtures';

test.describe('New Feature', () => {
  test.beforeEach(async ({ page, mockAPI }) => {
    await page.goto('/new-feature');
  });

  test('should display title', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /title/i })).toBeVisible();
  });
});
```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Selectors Guide](https://playwright.dev/docs/selectors)
- [Test Generator](https://playwright.dev/docs/codegen)

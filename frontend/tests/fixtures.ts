import { test as base, expect } from '@playwright/test';

// Mock API responses
export const mockApplications = [
  {
    id: 1,
    application_ref: 'APP-2025-001',
    applicant_name: 'John Smith',
    created_at: '2025-01-01T10:00:00Z',
    status: 'completed',
    run_id: 1,
  },
  {
    id: 2,
    application_ref: 'APP-2025-002',
    applicant_name: 'Jane Doe',
    created_at: '2025-01-02T11:00:00Z',
    status: 'processing',
    run_id: 2,
  },
];

export const mockRuns = [
  {
    id: 1,
    run_type: 'ui_single',
    application_id: 1,
    started_at: '2025-01-01T10:00:00Z',
    completed_at: '2025-01-01T10:05:00Z',
    status: 'completed',
    run_metadata: { application_ref: 'APP-2025-001' },
  },
  {
    id: 2,
    run_type: 'ui_batch',
    application_id: 2,
    started_at: '2025-01-02T11:00:00Z',
    completed_at: null,
    status: 'running',
    run_metadata: { application_ref: 'APP-2025-002' },
  },
];

export const mockRunResults = {
  summary: {
    total_documents: 5,
    processed: 5,
    errors: 0,
  },
  llm_calls_per_run: 12,
  findings: [
    {
      rule_id: 'RULE-001',
      severity: 'critical',
      message: 'Missing site plan document',
      details: { document_type: 'site_plan' },
    },
    {
      rule_id: 'RULE-002',
      severity: 'warning',
      message: 'Incomplete applicant information',
      details: { field: 'contact_email' },
    },
  ],
};

// Custom fixture for API mocking
type TestFixtures = {
  mockAPI: void;
};

export const test = base.extend<TestFixtures>({
  mockAPI: async ({ page }, use) => {
    // Mock API responses
    await page.route('**/api/applications*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ applications: mockApplications }),
      });
    });

    await page.route('**/api/runs*', (route) => {
      if (route.request().url().includes('/results')) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockRunResults),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ runs: mockRuns }),
        });
      }
    });

    await page.route('**/api/upload*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ run_id: 3, message: 'Upload successful' }),
      });
    });

    await use();
  },
});

export { expect };

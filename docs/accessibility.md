# Quick Reference: HIL Review & Accessibility Features

## Authentication & Authorization

### Get Current User Info
```typescript
import { api } from './api/client';

// Get user info from JWT token
const userInfo = await api.getUserInfo();
// Returns: { user_id, role, auth_type }

// Check if user has specific role
const canReview = await api.checkUserRole(['officer', 'admin', 'reviewer']);
```

### Submit Review Decision (with auth)
```typescript
// Now uses real user_id from JWT token
await api.submitReviewDecision(runId, checkId, 'accept', 'Optional comment');
```

## Download Review Report

```typescript
import { api } from './api/client';

// Download PDF report
const handleDownload = async () => {
  const blob = await api.downloadReviewReport(runId);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `review_report_${runId}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};
```

## LLM Call Tracker

```typescript
import LLMCallTracker from './components/LLMCallTracker';

const llmCalls = [
  {
    timestamp: '2024-01-15T10:30:00Z',
    purpose: 'Building height validation',
    rule_type: 'height_restriction',
    tokens_used: 1250,
    model: 'gpt-4',
    response_time_ms: 850
  }
];

<LLMCallTracker
  calls={llmCalls}
  totalTokens={1250}
  totalCalls={1}
  showDetails={false}
/>
```

## Accessibility Utilities

### Screen Reader Announcements
```typescript
import { announceToScreenReader } from './utils/accessibility';

// Polite announcement (non-urgent)
announceToScreenReader('Form saved successfully', 'polite');

// Assertive announcement (urgent)
announceToScreenReader('Error: validation failed', 'assertive');
```

### Keyboard Navigation
```typescript
import { handleKeyboardNavigation } from './utils/accessibility';

<div
  tabIndex={0}
  onKeyDown={(e) => handleKeyboardNavigation(e, handleClick)}
>
  Interactive element
</div>
```

### Focus Management
```typescript
import { FocusTrap } from './utils/accessibility';

const dialogRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (isOpen && dialogRef.current) {
    const trap = new FocusTrap(dialogRef.current);
    trap.activate();
    return () => trap.deactivate();
  }
}, [isOpen]);
```

### Button ARIA Props
```typescript
import { getButtonAriaProps } from './utils/accessibility';

<button
  {...getButtonAriaProps({
    isPressed: isActive,
    isExpanded: isOpen,
    controls: 'dropdown-menu',
    isDisabled: loading
  })}
>
  Toggle Menu
</button>
```

### Color Contrast Check
```typescript
import { checkColorContrast } from './utils/accessibility';

const result = checkColorContrast('#1976d2', '#ffffff');
// Returns: { ratio: 4.63, passesAA: true, passesAAA: false }
```

### Skip to Main Content
```typescript
import { skipToMainContent } from './utils/accessibility';

<a
  href="#main-content"
  className="skip-link"
  onClick={(e) => {
    e.preventDefault();
    skipToMainContent('main-content');
  }}
>
  Skip to main content
</a>
```

## Accessibility CSS Classes

### Screen Reader Only
```html
<span class="sr-only">Loading...</span>
```

### High Contrast Text
```html
<div class="high-contrast-text">Important message</div>
```

## ARIA Labels Best Practices

### Navigation
```tsx
<nav aria-label="Main navigation">
  <ListItemButton
    aria-label="Navigate to Dashboard"
    aria-current={isActive ? 'page' : undefined}
  >
    Dashboard
  </ListItemButton>
</nav>
```

### Buttons
```tsx
<Button
  aria-label="Delete item"
  aria-describedby="delete-description"
>
  <DeleteIcon aria-hidden="true" />
</Button>
<span id="delete-description" className="sr-only">
  This action cannot be undone
</span>
```

### Forms
```tsx
<TextField
  label="Email"
  aria-label="Enter your email address"
  aria-invalid={hasError}
  aria-describedby={hasError ? 'email-error' : undefined}
/>
{hasError && (
  <span id="email-error" className="error-message">
    Please enter a valid email
  </span>
)}
```

## Testing Commands

### Run Frontend Tests
```bash
cd frontend
npm run test
```

### Check Accessibility
```bash
cd frontend
npm run test:a11y  # If configured
```

### Manual Testing
1. **Keyboard Navigation**: Tab through all interactive elements
2. **Screen Reader**: Test with NVDA (Windows) or VoiceOver (Mac)
3. **Color Contrast**: Use browser DevTools Accessibility panel
4. **Focus Indicators**: Tab and verify visible focus rings
5. **Skip Links**: Press Tab on page load to reveal skip link

## Common Issues & Solutions

### Issue: Focus indicator not visible
```css
/* Add to component CSS */
:focus-visible {
  outline: 3px solid #1976d2;
  outline-offset: 2px;
}
```

### Issue: Button too small on mobile
```css
/* Ensure minimum touch target */
button {
  min-width: 44px;
  min-height: 44px;
}
```

### Issue: Screen reader announces too much
```html
<!-- Use aria-hidden for decorative elements -->
<Icon aria-hidden="true" />
```

### Issue: Form validation not announced
```typescript
// Announce validation errors
if (errors.length > 0) {
  announceToScreenReader(
    `Form has ${errors.length} errors`,
    'assertive'
  );
}
```

## Backend Role Checking

```python
# In planproof/api/routes/review.py
def check_review_permission(user: dict) -> bool:
    allowed_roles = ['officer', 'admin', 'reviewer', 'planner']
    return user.get('role', 'guest') in allowed_roles

# Use in endpoint
if not check_review_permission(user):
    raise HTTPException(status_code=403, detail="Permission denied")
```

## Environment Setup

No additional environment variables required. Ensure JWT tokens include:
- `sub`: User ID
- `role`: User role (officer/admin/reviewer/planner/guest)

## Quick Checklist

- [ ] User authentication working
- [ ] RBAC permissions enforced
- [ ] Download report button functional
- [ ] LLM tracker displays correctly
- [ ] Skip link appears on Tab
- [ ] All buttons have ARIA labels
- [ ] Form errors announced to screen readers
- [ ] Color contrast ratio ≥ 4.5:1
- [ ] Touch targets ≥ 44x44px
- [ ] Keyboard navigation works throughout

---

**For detailed information, see IMPLEMENTATION_SUMMARY.md**

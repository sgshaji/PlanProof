# Migration Guide: Upgrading to New HIL Review System

## Overview
This guide helps you migrate from the old hardcoded review system to the new authenticated role-based system.

---

## 🔄 Breaking Changes

### 1. Reviewer ID is No Longer Hardcoded

**Before:**
```typescript
// Old code - hardcoded to 1
reviewer_id: 1
```

**After:**
```typescript
// New code - extracted from auth token
const userInfo = getUserInfo();
reviewer_id: userInfo.user_id
```

**Action Required:** None - handled automatically by the API client

---

### 2. HIL Review Requires Authentication

**Before:**
- Anyone could submit reviews
- No permission checks

**After:**
- Must have valid JWT token or API key
- Must have officer/admin/reviewer/planner role

**Action Required:**
```typescript
// Check user permissions before showing review UI
const userInfo = await api.checkUserRole();
if (!userInfo.can_review) {
  // Show error or redirect
  navigate('/unauthorized');
}
```

---

## 📝 Step-by-Step Migration

### Step 1: Update Frontend Dependencies
No new dependencies required - uses existing axios and MUI.

### Step 2: Replace Old Review Submission Code

**Before:**
```typescript
const submitReview = async () => {
  await axios.post('/api/v1/runs/${runId}/findings/${checkId}/review', {
    decision,
    comment,
    reviewer_id: 1  // ❌ Hardcoded
  });
};
```

**After:**
```typescript
import { api } from '../api/client';

const submitReview = async () => {
  await api.submitReviewDecision(runId, checkId, decision, comment);
  // ✅ reviewer_id extracted automatically from auth token
};
```

### Step 3: Add Permission Checks

Add this to the top of your review component:

```typescript
const [hasPermission, setHasPermission] = useState(false);

useEffect(() => {
  const checkPermissions = async () => {
    try {
      const userInfo = await api.checkUserRole();
      setHasPermission(userInfo.can_review);
      if (!userInfo.can_review) {
        setError('You do not have permission to perform reviews');
      }
    } catch (err) {
      console.error('Permission check failed:', err);
    }
  };
  
  checkPermissions();
}, []);

// Disable submit buttons if no permission
<Button disabled={!hasPermission}>Submit</Button>
```

### Step 4: Update Backend Routes (if custom)

**Before:**
```python
@router.post("/my-custom-review")
async def submit_review(request: ReviewRequest):
    # No auth check
    pass
```

**After:**
```python
from planproof.api.dependencies import get_current_user
from planproof.api.routes.review import check_review_permission

@router.post("/my-custom-review")
async def submit_review(
    request: ReviewRequest,
    user: dict = Depends(get_current_user)
):
    # Check permission
    if not check_review_permission(user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Use real user ID
    reviewer_id = user.get('user_id')
```

### Step 5: Set Up Authentication (if not already done)

**Option A: JWT Tokens (Recommended)**
```bash
# .env
JWT_SECRET_KEY=your-super-secret-key-here
JWT_EXPIRATION_MINUTES=480  # 8 hours
JWT_ALGORITHM=HS256
```

**Option B: API Keys**
```bash
# .env
API_KEYS=key1,key2,key3
```

**Option C: Development Mode (No Auth)**
```bash
# .env - Leave JWT_SECRET_KEY and API_KEYS unset
# System will allow anonymous access
```

### Step 6: Generate JWT Tokens for Users

```python
from planproof.api.dependencies import create_access_token
from datetime import timedelta

# Create token for user
token = create_access_token(
    data={
        "sub": "officer@council.gov",      # User ID
        "role": "officer",                 # User role
        "name": "John Smith",              # Optional
        "email": "officer@council.gov"     # Optional
    },
    expires_delta=timedelta(hours=8)
)

# Return token to user
return {"access_token": token, "token_type": "bearer"}
```

### Step 7: Store Token in Frontend

```typescript
// After login/authentication
const handleLogin = async (credentials) => {
  const response = await axios.post('/auth/login', credentials);
  const { access_token } = response.data;
  
  // Store token
  localStorage.setItem('token', access_token);
  
  // Optionally decode and store user info
  const payload = JSON.parse(atob(access_token.split('.')[1]));
  localStorage.setItem('user', JSON.stringify({
    user_id: payload.sub,
    role: payload.role
  }));
  
  // Redirect to app
  navigate('/dashboard');
};
```

---

## 🎯 Testing Your Migration

### Test 1: Verify Auth Token is Sent
```typescript
// Open browser DevTools > Network tab
// Submit a review
// Check request headers:
// Should include: Authorization: Bearer eyJhbGc...
```

### Test 2: Verify User ID is Correct
```typescript
// Check backend logs when submitting review
// Should show actual user email/ID, not "1"
```

### Test 3: Test Permission Denial
```python
# Create token with wrong role
token = create_access_token(data={"sub": "user@test.com", "role": "viewer"})

# Try to submit review
# Should get 403 Forbidden
```

### Test 4: Test Anonymous Access (Development)
```bash
# Remove JWT_SECRET_KEY from .env
# Restart server
# Should still work with anonymous access
```

---

## 🔧 Troubleshooting

### Problem: 401 Unauthorized
**Cause:** Token not being sent or invalid

**Solution:**
```typescript
// Check token exists
const token = localStorage.getItem('token');
console.log('Token:', token ? 'Present' : 'Missing');

// Check token is valid (not expired)
if (token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  const expiry = new Date(payload.exp * 1000);
  console.log('Token expires:', expiry);
  console.log('Is expired:', expiry < new Date());
}
```

### Problem: 403 Forbidden
**Cause:** User lacks required role

**Solution:**
```typescript
// Check user role
const userInfo = await api.checkUserRole();
console.log('User role:', userInfo.role);
console.log('Can review:', userInfo.can_review);

// Expected roles: officer, admin, reviewer, planner
```

### Problem: Still seeing reviewer_id = 1
**Cause:** Using old API client or direct axios

**Solution:**
```typescript
// ❌ Don't use direct axios
axios.post('/api/v1/runs/.../review', {...})

// ✅ Use API client wrapper
import { api } from '../api/client';
api.submitReviewDecision(...)
```

### Problem: Download report fails with 400
**Cause:** Review not marked as completed

**Solution:**
```typescript
// Ensure you call completeReview first
await api.completeReview(runId);

// Then download
await api.downloadReviewReport(runId);
```

---

## 📋 Checklist

Before deploying to production:

- [ ] Set JWT_SECRET_KEY environment variable
- [ ] Generate tokens for existing users
- [ ] Update user records with roles
- [ ] Test authentication flow end-to-end
- [ ] Verify permission checks work
- [ ] Test with different user roles
- [ ] Test report download functionality
- [ ] Remove any hardcoded reviewer_id references
- [ ] Update API documentation
- [ ] Train users on new login process
- [ ] Set up token refresh mechanism (if needed)
- [ ] Configure token expiration appropriately
- [ ] Test error scenarios (expired token, wrong role)
- [ ] Verify accessibility features work
- [ ] Test with keyboard navigation
- [ ] Test with screen reader

---

## 🚀 Deployment Steps

### 1. Backup Database
```bash
pg_dump planproof > backup_$(date +%Y%m%d).sql
```

### 2. Update Environment Variables
```bash
# Production .env
JWT_SECRET_KEY=generate-strong-random-key-here
JWT_EXPIRATION_MINUTES=480
API_CORS_ORIGINS=https://app.example.com
```

### 3. Deploy Backend
```bash
# Pull latest code
git pull origin main

# Restart API server
systemctl restart planproof-api
```

### 4. Deploy Frontend
```bash
# Build with new changes
cd frontend
npm run build

# Deploy dist/ folder to web server
```

### 5. Verify Deployment
```bash
# Check health endpoint
curl https://api.example.com/api/v1/health

# Check auth endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/api/v1/auth/user-info
```

---

## 📞 Support

If you encounter issues during migration:

1. Check the logs: `journalctl -u planproof-api -f`
2. Review error messages in browser console
3. Verify environment variables are set correctly
4. Test with curl commands to isolate frontend vs backend issues
5. Check [QUICK_REFERENCE_HIL_ACCESSIBILITY.md](QUICK_REFERENCE_HIL_ACCESSIBILITY.md) for examples

---

## 📚 Additional Resources

- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Full feature documentation
- [QUICK_REFERENCE_HIL_ACCESSIBILITY.md](QUICK_REFERENCE_HIL_ACCESSIBILITY.md) - Code examples
- Backend API docs: `http://localhost:8000/api/docs`

---

**Migration Completed?** ✅  
Mark this date: __________

**Tested By:** __________  
**Approved By:** __________  
**Deployed On:** __________

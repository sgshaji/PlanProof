# PlanProof UI - Testing Guide

**Status**: ✅ Ready for Testing
**Branch**: `claude/fix-app-screen-ui-LW99P`
**Last Updated**: 2026-01-02

---

## 🌐 Access the UI

### Using Claude Code Browser:
**URL**: http://localhost:3000/new-application

**Alternative**: http://21.0.0.150:3000/new-application

---

## ✅ What You Can Test (UI Features)

### 1. **Backend Connection Monitor**
- ✅ Should see **green alert**: "Backend server is connected and healthy"
- ✅ If backend stops, will show **red alert** with retry button
- ✅ Click retry to reconnect

### 2. **Application Reference Validation**
Try these in the "Application Reference" field:

**Invalid (should show red error)**:
- Empty field → "Application reference is required"
- `AB` → "Must be at least 3 characters"
- `APP@2025` → "Invalid characters (only alphanumeric, -, / allowed)"
- `APP 2025` → "Invalid characters (spaces not allowed)"
- `TEST#123` → "Invalid characters"

**Valid (should accept)**:
- `APP-2025-001` ✅
- `APP/2025/001` ✅
- `TEST-123` ✅
- `PLANNING-APP-001` ✅

### 3. **File Validation**
Try uploading these types of files:

**Should be rejected with warning**:
- Non-PDF file (.txt, .docx, .jpg) → "Only PDF files are allowed"
- Empty file (0 bytes) → "File is empty (0 bytes)"
- Same file twice → "File already added"
- Very large file (>200MB) → "Exceeds limit of 200MB"

**Should show warnings**:
- 100-150MB file → Yellow chip color
- 150-200MB file → Red chip color
- < 100MB file → Default color (green)

**Should accept**:
- Valid PDF file (.pdf extension)
- File size 1KB - 200MB
- Unique filenames

### 4. **File Management**
- ✅ Drag & drop PDF files
- ✅ Click to browse and select files
- ✅ Remove files before upload (X button)
- ✅ See file size displayed in MB
- ✅ See file count: "Selected Files (2)"

### 5. **Upload Attempt** (Will fail due to database)
When you click "Start Validation":

**Expected Behavior**:
1. ✅ Form validation runs first
2. ✅ Progress bars appear for each file
3. ✅ Individual file upload starts
4. ❌ **Upload will fail** with database error:
   - Error message: "failed to resolve host planproof-dev-pgflex..."
   - Each file shows red error icon
   - **Retry button appears** on each failed file

**What you can verify**:
- ✅ Progress tracking works (shows 0% → uploading → error)
- ✅ Error handling shows specific messages
- ✅ Retry buttons appear on failed files
- ✅ Can retry individual files
- ✅ Submit button disabled during upload
- ✅ Can't remove files during upload

### 6. **Error Messages**
Check that errors are clear and actionable:

**Network errors**:
- Backend offline → "Cannot connect to backend server"
- Timeout → "Upload timeout - please try again"

**Validation errors**:
- Missing app ref → "Application reference is required"
- Invalid format → "Can only contain letters, numbers, hyphens, slashes"
- No files → "Please upload at least one PDF document"

**File errors**:
- Wrong type → "Only PDF files are allowed"
- Too large → "File size 250.5MB exceeds limit of 200MB"
- Duplicate → "File already added"

---

## 🎨 UI Features to Verify

### Visual Feedback
- ✅ **Icons**: Checkmark (success), X (error), Spinner (uploading)
- ✅ **Colors**: Green (success), Red (error), Yellow (warning), Blue (info)
- ✅ **Progress bars**: Individual per file with percentage
- ✅ **Chips**: File size with color coding
- ✅ **Alerts**: Backend status, validation errors, upload errors
- ✅ **Tooltips**: Hover over file size chip

### Responsive Behavior
- ✅ Form fields disable during upload
- ✅ Drag zone disabled during upload
- ✅ Submit button shows spinner during upload
- ✅ Can't modify files during upload
- ✅ Retry buttons only appear on failed files

### User Flow
1. Open page → See backend status
2. Enter app reference → See validation
3. Add files → See file list with sizes
4. Click "Start Validation" → See progress
5. Upload fails (database) → See retry options
6. Can retry individual files

---

## ❌ Known Issues (Expected)

### Database Connection Failure
**Error**: All uploads will fail with:
```
failed to resolve host 'planproof-dev-pgflex-8016.postgres.database.azure.com'
```

**This is EXPECTED** - Azure PostgreSQL is not accessible from this environment.

**Impact**:
- Cannot create applications
- Cannot upload documents
- Cannot store results

**But you can still test**:
- ✅ All UI validation
- ✅ Form behavior
- ✅ Error handling
- ✅ Progress tracking
- ✅ Retry functionality

---

## 📊 Testing Checklist

### Basic Functionality
- [ ] Page loads without console errors
- [ ] Backend status shows green alert
- [ ] Can enter application reference
- [ ] Can enter applicant name
- [ ] Can drag & drop files
- [ ] Can click to browse files
- [ ] Can remove files before upload

### Validation
- [ ] Invalid app ref shows error
- [ ] Valid app ref is accepted
- [ ] Non-PDF files are rejected
- [ ] Empty files are rejected
- [ ] Duplicate files are rejected
- [ ] Large files show warning colors

### Upload Flow
- [ ] Progress bars appear
- [ ] Each file tracked individually
- [ ] Error messages are clear
- [ ] Retry buttons appear on failure
- [ ] Can retry individual files

### Edge Cases
- [ ] Try uploading 0 files → Shows error
- [ ] Try empty app ref → Shows error
- [ ] Try special characters in app ref → Shows error
- [ ] Add same file twice → Shows warning
- [ ] Remove all files → Submit button disabled

---

## 🔍 Console Checks

Open browser console (F12) and verify:

**Should see** ✅:
- No React errors (except DevTools notices)
- No CORS errors
- Backend health check succeeding

**Expected to see** ⚠️:
- Database connection errors (when uploading)
- This is normal/expected

**Should NOT see** ❌:
- `useEffect` / `useState` errors
- `checkBackendHealth` errors
- React Router warnings
- CORS blocking messages

---

## 🎯 Success Criteria

The UI is working correctly if:

1. ✅ **Page loads** - No console errors, all components render
2. ✅ **Backend connected** - Green alert showing
3. ✅ **Validation works** - Form rejects invalid input
4. ✅ **File handling works** - Can add/remove files
5. ✅ **Progress tracking works** - Individual file progress shown
6. ✅ **Errors are clear** - Specific, actionable error messages
7. ✅ **Retry works** - Can retry failed uploads

**Expected failure**: Database connection during upload (not a UI bug)

---

## 📝 What's Fixed

### 28 Total Bugs Fixed:
- ✅ Backend server configuration
- ✅ CORS errors resolved
- ✅ useEffect/useState bug
- ✅ React Router warnings
- ✅ Per-file progress tracking
- ✅ File validation (size, format, duplicates)
- ✅ App reference validation
- ✅ Backend health monitoring
- ✅ Enhanced error messages
- ✅ Retry functionality
- ✅ API timeout handling
- ✅ Network error detection
- ✅ Loading states
- ✅ Visual feedback (icons, colors)
- ✅ Smart navigation
- ✅ Form state management

---

## 🚀 Quick Test Scenarios

### Scenario 1: Happy Path (until database error)
1. Open http://localhost:3000/new-application
2. See green "Backend connected" alert ✅
3. Enter `APP-2025-TEST`
4. Upload a PDF file
5. Click "Start Validation"
6. See progress bar for file ✅
7. See database error (expected) ❌
8. See retry button ✅

### Scenario 2: Validation Testing
1. Try empty app ref → See error ✅
2. Try `AB` → See "at least 3 characters" ✅
3. Try `APP@123` → See "invalid characters" ✅
4. Try uploading .txt file → See rejection ✅
5. Add file twice → See duplicate warning ✅

### Scenario 3: Error Recovery
1. Upload files → Fails with database error ❌
2. See retry buttons on each file ✅
3. Click retry → Attempts upload again ✅
4. Still fails (database) but UI handles gracefully ✅

---

**Ready to test!** Open http://localhost:3000/new-application in Claude Code's browser.

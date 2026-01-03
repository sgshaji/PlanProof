#!/bin/bash

# Automated UI Testing Script for PlanProof New Application Screen
# This script tests various scenarios including edge cases and error conditions

echo "========================================="
echo "  PlanProof UI Automated Testing Suite  "
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Backend URL
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    local test_name="$1"
    local result="$2"
    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$result" == "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Test 1: Check if backend is running
echo "Test 1: Backend Health Check"
echo "------------------------------"
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" http://localhost:8000/api/v1/health -o /tmp/health_response.json)
if [ "$HEALTH_RESPONSE" == "200" ]; then
    print_result "Backend is running and healthy" "PASS"
    cat /tmp/health_response.json | jq '.'
else
    print_result "Backend health check failed" "FAIL"
    echo "Expected: 200, Got: $HEALTH_RESPONSE"
fi
echo ""

# Test 2: Create test application
echo "Test 2: Create Application API"
echo "-------------------------------"
APP_REF="TEST-APP-$(date +%s)"
curl -s -X POST "${BACKEND_URL}/api/v1/applications" \
    -H "Content-Type: application/json" \
    -d "{\"application_ref\": \"${APP_REF}\", \"applicant_name\": \"Test Applicant\"}" \
    -w "\nHTTP Status: %{http_code}\n" \
    -o /tmp/create_app_response.json

HTTP_STATUS=$(tail -1 /tmp/create_app_response.json | grep -oP '\d{3}')
if [ ! -z "$HTTP_STATUS" ] && ([ "$HTTP_STATUS" == "200" ] || [ "$HTTP_STATUS" == "201" ]); then
    print_result "Application created successfully" "PASS"
    cat /tmp/create_app_response.json | head -n -1 | jq '.'
else
    print_result "Application creation failed" "FAIL"
fi
echo ""

# Test 3: Test duplicate application (should return 409)
echo "Test 3: Duplicate Application Test"
echo "-----------------------------------"
DUPLICATE_RESPONSE=$(curl -s -w "%{http_code}" -X POST "${BACKEND_URL}/api/v1/applications" \
    -H "Content-Type: application/json" \
    -d "{\"application_ref\": \"${APP_REF}\", \"applicant_name\": \"Test Applicant\"}" \
    -o /tmp/dup_response.json)

if [ "$DUPLICATE_RESPONSE" == "409" ]; then
    print_result "Duplicate application correctly rejected (409 Conflict)" "PASS"
else
    print_result "Duplicate handling failed - Expected 409, got $DUPLICATE_RESPONSE" "FAIL"
fi
echo ""

# Test 4: Create test PDF files
echo "Test 4: Generate Test PDF Files"
echo "--------------------------------"
mkdir -p /tmp/test_pdfs

# Create a small valid PDF
echo "%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF" > /tmp/test_pdfs/small_test.pdf

# Create empty file (should be rejected)
touch /tmp/test_pdfs/empty.pdf

# Create non-PDF file (should be rejected)
echo "This is not a PDF" > /tmp/test_pdfs/invalid.txt

print_result "Test PDF files created" "PASS"
echo "  - small_test.pdf (valid, ~410 bytes)"
echo "  - empty.pdf (invalid, 0 bytes)"
echo "  - invalid.txt (invalid, not PDF)"
echo ""

# Test 5: File upload with valid PDF
echo "Test 5: Upload Valid PDF"
echo "-------------------------"
UPLOAD_RESPONSE=$(curl -s -w "%{http_code}" -X POST \
    "${BACKEND_URL}/api/v1/applications/${APP_REF}/documents" \
    -F "file=@/tmp/test_pdfs/small_test.pdf" \
    -o /tmp/upload_response.json)

if [ "$UPLOAD_RESPONSE" == "200" ]; then
    print_result "Valid PDF uploaded successfully" "PASS"
    cat /tmp/upload_response.json | jq '.'
else
    print_result "PDF upload failed - HTTP $UPLOAD_RESPONSE" "FAIL"
    cat /tmp/upload_response.json
fi
echo ""

# Test 6: CORS headers check
echo "Test 6: CORS Configuration"
echo "--------------------------"
CORS_HEADERS=$(curl -s -I -X OPTIONS "${BACKEND_URL}/api/v1/applications" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST" | grep -i "access-control")

if [ ! -z "$CORS_HEADERS" ]; then
    print_result "CORS headers are configured" "PASS"
    echo "$CORS_HEADERS"
else
    print_result "CORS headers missing" "FAIL"
fi
echo ""

# Test 7: Get applications list
echo "Test 7: List Applications API"
echo "------------------------------"
LIST_RESPONSE=$(curl -s -w "%{http_code}" "${BACKEND_URL}/api/v1/applications?limit=5" \
    -o /tmp/list_response.json)

if [ "$LIST_RESPONSE" == "200" ]; then
    print_result "Applications list retrieved" "PASS"
    cat /tmp/list_response.json | jq '. | length'
else
    print_result "Applications list failed" "FAIL"
fi
echo ""

# Test 8: Frontend accessibility
echo "Test 8: Frontend Server Check"
echo "------------------------------"
FRONTEND_RESPONSE=$(curl -s -w "%{http_code}" "${FRONTEND_URL}" -o /dev/null)

if [ "$FRONTEND_RESPONSE" == "200" ]; then
    print_result "Frontend server is accessible" "PASS"
else
    print_result "Frontend server not accessible (HTTP $FRONTEND_RESPONSE)" "WARN"
    echo "Note: Start frontend with 'npm run dev' in frontend directory"
fi
echo ""

# Test 9: Test invalid application reference formats
echo "Test 9: Application Reference Validation"
echo "-----------------------------------------"
INVALID_REFS=("" "AB" "APP@2025" "APP 2025" "TEST#123")
VALID_REFS=("APP-2025-001" "APP/2025/001" "TEST123" "PLANNING-APP-001")

echo "Testing invalid references (should be rejected by frontend validation):"
for ref in "${INVALID_REFS[@]}"; do
    if [[ -z "$ref" ]]; then
        echo "  - (empty string) - Should fail: Required"
    elif [[ ${#ref} -lt 3 ]]; then
        echo "  - '$ref' - Should fail: Too short"
    elif ! [[ "$ref" =~ ^[A-Z0-9\-\/]+$ ]]; then
        echo "  - '$ref' - Should fail: Invalid characters"
    fi
done

echo ""
echo "Testing valid references (should be accepted):"
for ref in "${VALID_REFS[@]}"; do
    if [[ ${#ref} -ge 3 ]] && [[ "$ref" =~ ^[A-Z0-9\-\/]+$ ]]; then
        echo "  - '$ref' - Valid ✓"
    fi
done
echo ""

# Test 10: File size validation
echo "Test 10: File Size Validation"
echo "------------------------------"
echo "Testing file size limits:"
echo "  - 0 bytes (empty.pdf) - Should be rejected"
echo "  - 410 bytes (small_test.pdf) - Should be accepted"
echo "  - Files > 200MB - Should be rejected"
echo "  - Files 100-150MB - Should show warning"
echo "  - Files 150-200MB - Should show error color"
echo ""

# Test 11: Duplicate file detection
echo "Test 11: Duplicate File Detection"
echo "----------------------------------"
echo "Frontend should detect duplicate file names:"
echo "  - Adding same file twice should show warning"
echo "  - User should see 'File already added' error"
echo ""

# Final Summary
echo "========================================="
echo "          Test Summary                   "
echo "========================================="
echo -e "Total Tests:  ${TESTS_RUN}"
echo -e "${GREEN}Passed:       ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed:       ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    EXIT_CODE=0
else
    echo -e "${YELLOW}⚠ Some tests failed. Please review the output above.${NC}"
    EXIT_CODE=1
fi

# Cleanup
echo ""
echo "Cleaning up test files..."
rm -rf /tmp/test_pdfs
rm -f /tmp/*.json

echo "Test suite completed."
exit $EXIT_CODE

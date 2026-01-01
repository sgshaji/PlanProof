"""
Test the FastAPI REST API endpoints.

Start the API first: python run_api.py
Then run this script: python test_api.py
"""

import requests
import time

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

print("=" * 60)
print("🚀 Testing PlanProof REST API")
print("=" * 60)

# Wait for server to be ready
print("\n⏳ Waiting for API server...")
for i in range(10):
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ API server is ready!")
            break
    except:
        if i == 9:
            print("❌ API server not responding. Please start it with: python run_api.py")
            exit(1)
        time.sleep(1)

# Test 1: Root endpoint
print("\n1️⃣  Testing root endpoint...")
response = requests.get(BASE_URL)
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 2: Health check
print("\n2️⃣  Testing health endpoint...")
response = requests.get(f"{API_BASE}/health")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 3: Database health
print("\n3️⃣  Testing database health...")
response = requests.get(f"{API_BASE}/health/db")
print(f"   Status: {response.status_code}")
result = response.json()
print(f"   Database: {result.get('database', 'unknown')}")
print(f"   Applications: {result.get('applications_count', 0)}")

# Test 4: List applications
print("\n4️⃣  Testing list applications...")
response = requests.get(f"{API_BASE}/applications")
print(f"   Status: {response.status_code}")
apps = response.json()
print(f"   Found {len(apps)} applications")
if apps:
    print(f"   Latest: {apps[0]['application_ref']}")

# Test 5: Get specific application
if apps:
    print("\n5️⃣  Testing get application details...")
    app_ref = apps[0]['application_ref']
    response = requests.get(f"{API_BASE}/applications/{app_ref}")
    print(f"   Status: {response.status_code}")
    app_details = response.json()
    print(f"   Application: {app_details['application_ref']}")
    print(f"   Submissions: {len(app_details.get('submissions', []))}")

# Test 6: Create new application
print("\n6️⃣  Testing create application...")
test_app_ref = f"TEST-API-{int(time.time())}"
response = requests.post(
    f"{API_BASE}/applications",
    json={
        "application_ref": test_app_ref,
        "applicant_name": "API Test User"
    }
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"   Created: {result['application_ref']}")
    print(f"   ID: {result['id']}")

print("\n" + "=" * 60)
print("✅ API Tests Complete!")
print("=" * 60)
print("\n📖 API Documentation:")
print(f"   Swagger UI: {BASE_URL}/api/docs")
print(f"   ReDoc: {BASE_URL}/api/redoc")
print(f"   OpenAPI Spec: {BASE_URL}/api/openapi.json")
print("\n📝 Integration Guide: docs/API_INTEGRATION_GUIDE.md\n")

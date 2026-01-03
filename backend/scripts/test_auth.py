"""Test authentication dependencies to diagnose timeout."""

import sys
from pathlib import Path
import asyncio

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from planproof.api.dependencies import verify_api_key, verify_jwt_token, get_current_user


async def test_auth_dependencies():
    """Test authentication dependencies."""
    
    print("🔍 Testing authentication dependencies...")
    
    # Test 1: verify_api_key with no header
    print("\n1️⃣ Testing verify_api_key with no header...")
    try:
        result = await verify_api_key(x_api_key=None)
        print(f"   ✓ Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: verify_jwt_token with no credentials
    print("\n2️⃣ Testing verify_jwt_token with no credentials...")
    try:
        result = await verify_jwt_token(credentials=None)
        print(f"   ✓ Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: get_current_user with no auth
    print("\n3️⃣ Testing get_current_user (combined)...")
    try:
        # Simulate what FastAPI does - call both dependencies
        api_key_result = await verify_api_key(x_api_key=None)
        jwt_result = await verify_jwt_token(credentials=None)
        
        print(f"   - API key result: {api_key_result}")
        print(f"   - JWT result: {jwt_result}")
        
        # Now call get_current_user with results
        user = await get_current_user(api_key=api_key_result, jwt_payload=jwt_result)
        print(f"   ✓ User: {user}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n✅ Auth tests completed!")


if __name__ == "__main__":
    asyncio.run(test_auth_dependencies())

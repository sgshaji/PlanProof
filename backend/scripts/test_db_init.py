"""Test creating multiple Database instances to see if it causes slowdown."""

import sys
from pathlib import Path
import time

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from planproof.db import Database


def test_database_initialization():
    """Test creating multiple Database instances."""
    
    print("🔍 Testing Database initialization...")
    
    # Test creating multiple instances (simulating multiple requests)
    times = []
    
    for i in range(5):
        start = time.time()
        db = Database()
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"Instance {i+1}: {elapsed:.3f}s")
    
    avg_time = sum(times) / len(times)
    print(f"\n📊 Average initialization time: {avg_time:.3f}s")
    print(f"⚠️  Creating a new Database (with connection pool) for EACH request is inefficient!")
    print(f"💡 Recommendation: Use a singleton pattern or dependency injection with caching")


if __name__ == "__main__":
    test_database_initialization()

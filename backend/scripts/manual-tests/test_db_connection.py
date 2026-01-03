#!/usr/bin/env python3
"""
Quick test script to verify database connection.
"""

from planproof.db import Database
from planproof.db import Application, Document, Run

print("=" * 60)
print("🔍 Testing PlanProof Database Connection")
print("=" * 60)

try:
    # Test 1: Initialize database connection
    print("\n1️⃣  Testing database initialization...")
    db = Database()
    print("   ✅ Database class initialized")
    print(f"   📊 Driver: psycopg v3")
    print(f"   🗄️  Database: {db.engine.url.database}")
    print(f"   🌐 Host: {db.engine.url.host}")
    
    # Test 2: Get session
    print("\n2️⃣  Testing session creation...")
    session = db.get_session()
    print("   ✅ Session created successfully")
    
    # Test 3: Query applications (read test)
    print("\n3️⃣  Testing database READ access...")
    count = session.query(Application).count()
    print(f"   ✅ Query successful")
    print(f"   📋 Total applications: {count}")
    
    if count > 0:
        latest_app = session.query(Application).order_by(Application.created_at.desc()).first()
        print(f"   📌 Latest application: {latest_app.application_ref}")
    
    # Test 4: Query documents
    doc_count = session.query(Document).count()
    print(f"   📄 Total documents: {doc_count}")
    
    # Test 5: Query runs
    run_count = session.query(Run).count()
    print(f"   🏃 Total runs: {run_count}")
    
    session.close()
    
    # Test 6: Write test (create and delete)
    print("\n4️⃣  Testing database WRITE access...")
    test_app = db.create_application(
        application_ref="TEST-CONNECTION-2026",
        applicant_name="Database Connection Test"
    )
    print(f"   ✅ Created test application ID: {test_app.id}")
    
    # Clean up test data
    session = db.get_session()
    session.delete(test_app)
    session.commit()
    session.close()
    print("   🗑️  Test data cleaned up")
    
    print("\n" + "=" * 60)
    print("✅ ALL DATABASE TESTS PASSED!")
    print("=" * 60)
    print("\n🎉 Database connection is fully operational!")
    print("   Ready for MVP deployment.\n")
    
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ DATABASE TEST FAILED!")
    print("=" * 60)
    print(f"\n🚨 Error: {type(e).__name__}")
    print(f"📝 Message: {str(e)}\n")
    import traceback
    traceback.print_exc()
    exit(1)

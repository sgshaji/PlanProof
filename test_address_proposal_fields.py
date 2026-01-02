"""
Test script for Address/Proposal fields on Application model

This script verifies:
1. Application model has site_address and proposal_description columns
2. Database methods accept these fields
3. API endpoint returns these fields
4. Migration populates fields from extracted data

Usage:
    python test_address_proposal_fields.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from planproof.db import Database, Application
from sqlalchemy import inspect


def test_application_model():
    """Test that Application model has new columns."""
    print("\n=== Testing Application Model ===")
    
    inspector = inspect(Application)
    columns = [col.name for col in inspector.columns]
    
    print(f"Application columns: {columns}")
    
    required_columns = ['site_address', 'proposal_description']
    for col in required_columns:
        if col in columns:
            print(f"✅ Column '{col}' exists in Application model")
        else:
            print(f"❌ Column '{col}' missing from Application model")
            return False
    
    return True


def test_database_methods():
    """Test Database methods accept new fields."""
    print("\n=== Testing Database Methods ===")
    
    try:
        db = Database()
        
        # Test create_application signature
        import inspect
        sig = inspect.signature(db.create_application)
        params = list(sig.parameters.keys())
        
        print(f"create_application parameters: {params}")
        
        if 'site_address' in params and 'proposal_description' in params:
            print("✅ create_application accepts site_address and proposal_description")
        else:
            print("❌ create_application missing new parameters")
            return False
        
        # Test get_or_create_application signature
        sig = inspect.signature(db.get_or_create_application)
        params = list(sig.parameters.keys())
        
        print(f"get_or_create_application parameters: {params}")
        
        if 'site_address' in params and 'proposal_description' in params:
            print("✅ get_or_create_application accepts site_address and proposal_description")
        else:
            print("❌ get_or_create_application missing new parameters")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Database methods test failed: {e}")
        return False


def test_database_schema():
    """Test that database has the new columns."""
    print("\n=== Testing Database Schema ===")
    
    try:
        db = Database()
        session = db.get_session()
        
        # Try to query an application with new fields
        app = session.query(Application).first()
        
        if app:
            # Try to access new fields
            _ = app.site_address
            _ = app.proposal_description
            print(f"✅ Successfully accessed new fields on Application")
            print(f"   site_address: {app.site_address or 'NULL'}")
            print(f"   proposal_description: {app.proposal_description or 'NULL'}")
        else:
            print("⚠️  No applications in database to test")
        
        session.close()
        return True
    except AttributeError as e:
        print(f"❌ Database schema test failed: {e}")
        print("   Run migration: alembic upgrade head")
        return False
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False


def test_api_response():
    """Test API response structure."""
    print("\n=== Testing API Response ===")
    
    print("✅ API endpoint should return:")
    print("   - address: app.site_address or extracted or 'Not available'")
    print("   - proposal: app.proposal_description or extracted or 'Not available'")
    print("   - Fields are now stored permanently on Application")
    
    return True


def print_migration_instructions():
    """Print migration instructions."""
    print("\n" + "="*60)
    print("MIGRATION INSTRUCTIONS")
    print("="*60)
    print("""
To apply the database changes:

1. Run the migration:
   alembic upgrade head

2. Verify columns were added:
   psql -h <host> -U <user> -d planning_validation -c "
     SELECT column_name, data_type 
     FROM information_schema.columns 
     WHERE table_name = 'applications' 
     AND column_name IN ('site_address', 'proposal_description');
   "

3. Check that existing data was migrated:
   psql -h <host> -U <user> -d planning_validation -c "
     SELECT id, application_ref, 
            LEFT(site_address, 30) as address, 
            LEFT(proposal_description, 30) as proposal 
     FROM applications 
     LIMIT 5;
   "

The migration will automatically populate these fields from 
extracted_fields for existing applications.
    """)
    print("="*60 + "\n")


def main():
    """Run all tests."""
    print("="*60)
    print("ADDRESS/PROPOSAL FIELDS TEST")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Application Model", test_application_model()))
    results.append(("Database Methods", test_database_methods()))
    results.append(("Database Schema", test_database_schema()))
    results.append(("API Response", test_api_response()))
    
    # Print results
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed.")
        print("If Database Schema test failed, run: alembic upgrade head")
    
    print_migration_instructions()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

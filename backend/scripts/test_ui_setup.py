#!/usr/bin/env python3
"""
Test script to verify UI setup and dependencies.
"""

import sys
import io
import os
from pathlib import Path

# Fix Windows console encoding for emoji
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import streamlit
        print("  ✅ streamlit")
    except ImportError:
        print("  ❌ streamlit - Install with: pip install streamlit")
        return False
    
    try:
        from planproof.ui.main import st
        print("  ✅ planproof.ui.main")
    except ImportError as e:
        print(f"  ❌ planproof.ui.main - {e}")
        return False
    
    try:
        from planproof.ui.run_orchestrator import start_run, get_run_status, get_run_results
        print("  ✅ planproof.ui.run_orchestrator")
    except ImportError as e:
        print(f"  ❌ planproof.ui.run_orchestrator - {e}")
        return False
    
    try:
        from planproof.ui.pages import upload, status, results
        print("  ✅ planproof.ui.pages")
    except ImportError as e:
        print(f"  ❌ planproof.ui.pages - {e}")
        return False
    
    try:
        from planproof.db import Database
        print("  ✅ planproof.db")
    except ImportError as e:
        print(f"  ❌ planproof.db - {e}")
        return False
    
    try:
        from planproof.storage import StorageClient
        print("  ✅ planproof.storage")
    except ImportError as e:
        print(f"  ❌ planproof.storage - {e}")
        return False
    
    try:
        from planproof.docintel import DocumentIntelligence
        print("  ✅ planproof.docintel")
    except ImportError as e:
        print(f"  ❌ planproof.docintel - {e}")
        return False
    
    try:
        from planproof.aoai import AzureOpenAIClient
        print("  ✅ planproof.aoai")
    except ImportError as e:
        print(f"  ❌ planproof.aoai - {e}")
        return False
    
    return True


def test_file_structure():
    """Test that required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        "planproof/ui/main.py",
        "planproof/ui/run_orchestrator.py",
        "planproof/ui/pages/upload.py",
        "planproof/ui/pages/status.py",
        "planproof/ui/pages/results.py",
        "planproof/ui/__init__.py",
        "planproof/ui/pages/__init__.py",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - Missing!")
            all_exist = False
    
    return all_exist


def test_rule_catalog():
    """Test that rule catalog exists."""
    print("\nTesting rule catalog...")
    
    catalog_path = Path("artefacts/rule_catalog.json")
    if catalog_path.exists():
        print(f"  ✅ Rule catalog exists: {catalog_path}")
        
        # Try to load it
        try:
            import json
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
            rule_count = len(catalog.get("rules", []))
            print(f"  ✅ Rule catalog is valid JSON with {rule_count} rules")
            return True
        except Exception as e:
            print(f"  ❌ Rule catalog is invalid: {e}")
            return False
    else:
        print(f"  ❌ Rule catalog not found: {catalog_path}")
        print("  💡 Run: python scripts/build_rule_catalog.py")
        return False


def test_config():
    """Test that configuration is available."""
    print("\nTesting configuration...")
    
    try:
        from planproof.config import get_settings
        settings = get_settings()
        
        checks = [
            ("Database URL", getattr(settings, 'database_url', None)),
            ("Storage Connection", getattr(settings, 'azure_storage_connection_string', None)),
            ("DocIntel Endpoint", getattr(settings, 'azure_docintel_endpoint', None)),
            ("DocIntel Key", getattr(settings, 'azure_docintel_key', None)),
            ("OpenAI Endpoint", getattr(settings, 'azure_openai_endpoint', None)),
            ("OpenAI Key", getattr(settings, 'azure_openai_api_key', None)),
        ]
        
        # Check for deployment name with fallback (try both possible names)
        deployment = getattr(settings, 'azure_openai_chat_deployment', None) or getattr(settings, 'azure_openai_deployment_name', None)
        checks.append(("OpenAI Deployment", deployment))
        
        all_ok = True
        for name, value in checks:
            if value:
                print(f"  ✅ {name}")
            else:
                print(f"  ⚠️  {name} - Not set (may be optional)")
                # Don't fail on missing config, just warn
        
        return True
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False


def test_database_connection():
    """Test database connection."""
    print("\nTesting database connection...")
    
    try:
        from planproof.db import Database
        db = Database()
        
        # Try to create a session
        session = db.get_session()
        session.close()
        print("  ✅ Database connection successful")
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        print("  💡 Check DATABASE_URL in .env file")
        return False


def test_run_directories():
    """Test that run directories can be created."""
    print("\nTesting run directories...")
    
    try:
        test_dir = Path("./runs/test")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write
        test_file = test_dir / "test.txt"
        test_file.write_text("test")
        
        # Clean up
        test_file.unlink()
        test_dir.rmdir()
        
        print("  ✅ Run directories can be created and written to")
        return True
    except Exception as e:
        print(f"  ❌ Run directory test failed: {e}")
        print("  💡 Check write permissions in project directory")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("PlanProof UI Setup Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("File Structure", test_file_structure),
        ("Rule Catalog", test_rule_catalog),
        ("Configuration", test_config),
        ("Database Connection", test_database_connection),
        ("Run Directories", test_run_directories),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ❌ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! UI should be ready to run.")
        print("\nTo start the UI:")
        print("  streamlit run planproof/ui/main.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before running UI.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


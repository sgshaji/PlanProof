"""
Create all database tables (including new relational tables).

Run this before running migrate_to_relational_tables.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from planproof.db import Database

def main():
    """Create all tables."""
    print("Creating all database tables...")
    print("=" * 60)
    
    db = Database()
    db.create_tables()
    
    print("\n" + "=" * 60)
    print("Tables created successfully!")
    print("\nYou can now run: python scripts/migrate_to_relational_tables.py")

if __name__ == "__main__":
    main()


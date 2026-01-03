"""
Schema migration: Add new columns to existing tables.

This adds:
- submission_id to documents table
- document_type to documents table
- Any other new columns needed for relational tables
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from planproof.db import Database

def main():
    """Add new columns to existing tables."""
    print("Migrating database schema...")
    print("=" * 60)
    
    db = Database()
    session = db.get_session()
    
    try:
        from sqlalchemy import text
        
        # Add submission_id column to documents if it doesn't exist
        print("\n1. Adding submission_id column to documents table...")
        try:
            # Check if column exists
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='submission_id';
            """)).fetchall()
            
            if not result:
                # Column doesn't exist, add it
                session.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN submission_id INTEGER;
                """))
                session.commit()
                print("   OK: Added submission_id column")
            else:
                print("   OK: submission_id column already exists")
            
            # Add index if it doesn't exist
            try:
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_documents_submission_id 
                    ON documents(submission_id);
                """))
                session.commit()
            except:
                session.rollback()
                pass  # Index might already exist
            
            # Add foreign key if it doesn't exist
            try:
                fk_result = session.execute(text("""
                    SELECT COUNT(*) as count FROM pg_constraint 
                    WHERE conname = 'fk_documents_submission_id';
                """)).scalar()
                if fk_result == 0:
                    session.execute(text("""
                        ALTER TABLE documents 
                        ADD CONSTRAINT fk_documents_submission_id 
                        FOREIGN KEY (submission_id) REFERENCES submissions(id);
                    """))
                    session.commit()
            except Exception as e:
                session.rollback()
                print(f"   Note: Foreign key constraint: {e}")
        
        except Exception as e:
            session.rollback()
            print(f"   Error: {e}")
        
        # Add document_type column to documents if it doesn't exist
        print("\n2. Adding document_type column to documents table...")
        try:
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='document_type';
            """)).fetchall()
            
            if not result:
                session.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN document_type VARCHAR(50);
                """))
                session.commit()
                print("   OK: Added document_type column")
            else:
                print("   OK: document_type column already exists")
        except Exception as e:
            session.rollback()
            print(f"   Error: {e}")
        
        print("\n" + "=" * 60)
        print("Schema migration completed!")
        print("\nYou can now run: python scripts/migrate_to_relational_tables.py")
        
    finally:
        session.close()

if __name__ == "__main__":
    main()


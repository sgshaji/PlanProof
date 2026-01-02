"""Quick fix to add missing database columns."""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# Use psycopg (v3) instead of psycopg2
if DATABASE_URL and "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
engine = create_engine(DATABASE_URL)

# Add missing columns to submissions table
with engine.connect() as conn:
    try:
        # Check if columns exist first
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'submissions' 
            AND column_name IN ('submission_type', 'submission_type_confidence', 'submission_type_source')
        """))
        existing_columns = {row[0] for row in result}
        
        # Add missing columns
        if 'submission_type' not in existing_columns:
            print("Adding submission_type column...")
            conn.execute(text("""
                ALTER TABLE submissions 
                ADD COLUMN submission_type VARCHAR(50)
            """))
            conn.commit()
            print("✅ Added submission_type")
        
        if 'submission_type_confidence' not in existing_columns:
            print("Adding submission_type_confidence column...")
            conn.execute(text("""
                ALTER TABLE submissions 
                ADD COLUMN submission_type_confidence FLOAT
            """))
            conn.commit()
            print("✅ Added submission_type_confidence")
        
        if 'submission_type_source' not in existing_columns:
            print("Adding submission_type_source column...")
            conn.execute(text("""
                ALTER TABLE submissions 
                ADD COLUMN submission_type_source VARCHAR(50)
            """))
            conn.commit()
            print("✅ Added submission_type_source")
        
        # Check runs table for run_type column
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'runs' 
            AND column_name = 'run_type'
        """))
        runs_columns = {row[0] for row in result}
        
        if 'run_type' not in runs_columns:
            print("Adding run_type column to runs table...")
            conn.execute(text("""
                ALTER TABLE runs 
                ADD COLUMN run_type VARCHAR(50) DEFAULT 'ui_single'
            """))
            conn.commit()
            print("✅ Added run_type to runs")
        
        print("\n✅ Database schema fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()

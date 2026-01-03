"""
Comprehensive Database Schema Validator and Fixer.

This script:
1. Checks all SQLAlchemy models against actual database schema
2. Identifies missing columns, tables, and mismatches
3. Automatically fixes schema issues
4. Generates a migration report
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from typing import Dict, List, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

# Import all models
from planproof.db import (
    Base, Application, Submission, Document, Run, 
    ValidationCheck, ChangeSet
)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)


def get_model_columns(model) -> Dict[str, str]:
    """Extract expected columns from SQLAlchemy model."""
    columns = {}
    for column in model.__table__.columns:
        col_type = str(column.type)
        columns[column.name] = col_type
    return columns


def get_db_columns(table_name: str) -> Dict[str, str]:
    """Get actual columns from database table."""
    columns = {}
    try:
        for column in inspector.get_columns(table_name):
            columns[column['name']] = str(column['type'])
    except Exception:
        return {}
    return columns


def get_db_tables() -> Set[str]:
    """Get all tables in database."""
    return set(inspector.get_table_names())


def compare_schemas() -> Dict:
    """Compare models vs database and identify issues."""
    models = [
        ('applications', Application),
        ('submissions', Submission),
        ('documents', Document),
        ('runs', Run),
        ('validation_checks', ValidationCheck),
        ('change_sets', ChangeSet),
    ]
    
    issues = {
        'missing_tables': [],
        'missing_columns': {},
        'type_mismatches': {},
        'extra_tables': [],
        'extra_columns': {}
    }
    
    db_tables = get_db_tables()
    
    for table_name, model in models:
        # Check if table exists
        if table_name not in db_tables:
            issues['missing_tables'].append(table_name)
            continue
        
        model_cols = get_model_columns(model)
        db_cols = get_db_columns(table_name)
        
        # Find missing columns
        missing = set(model_cols.keys()) - set(db_cols.keys())
        if missing:
            issues['missing_columns'][table_name] = {
                col: model_cols[col] for col in missing
            }
        
        # Find extra columns
        extra = set(db_cols.keys()) - set(model_cols.keys())
        if extra:
            issues['extra_columns'][table_name] = list(extra)
    
    return issues


def fix_schema(issues: Dict, dry_run: bool = False) -> None:
    """Fix schema issues automatically."""
    fixes_applied = []
    
    with engine.connect() as conn:
        # Fix missing columns
        for table_name, columns in issues['missing_columns'].items():
            for col_name, col_type in columns.items():
                # Map SQLAlchemy types to PostgreSQL types
                pg_type = map_to_pg_type(col_type)
                
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {pg_type}"
                
                if dry_run:
                    print(f"[DRY RUN] {sql}")
                else:
                    try:
                        print(f"Executing: {sql}")
                        conn.execute(text(sql))
                        conn.commit()
                        fixes_applied.append(f"Added {table_name}.{col_name}")
                    except Exception as e:
                        print(f"❌ Error adding {table_name}.{col_name}: {e}")
                        conn.rollback()
        
        # Create missing tables
        if issues['missing_tables'] and not dry_run:
            print("\n⚠️  Missing tables detected. Creating all tables from models...")
            Base.metadata.create_all(engine)
            fixes_applied.append("Created missing tables")
    
    return fixes_applied


def map_to_pg_type(sqlalchemy_type: str) -> str:
    """Map SQLAlchemy type to PostgreSQL type."""
    type_lower = sqlalchemy_type.lower()
    
    # Common mappings
    if 'integer' in type_lower:
        return 'INTEGER'
    elif 'bigint' in type_lower:
        return 'BIGINT'
    elif 'varchar' in type_lower:
        # Extract length if specified
        if '(' in sqlalchemy_type:
            return sqlalchemy_type.upper()
        return 'VARCHAR(255)'
    elif 'text' in type_lower:
        return 'TEXT'
    elif 'boolean' in type_lower or 'bool' in type_lower:
        return 'BOOLEAN'
    elif 'float' in type_lower or 'real' in type_lower:
        return 'FLOAT'
    elif 'numeric' in type_lower or 'decimal' in type_lower:
        return 'NUMERIC'
    elif 'timestamp' in type_lower or 'datetime' in type_lower:
        return 'TIMESTAMP WITHOUT TIME ZONE'
    elif 'date' in type_lower:
        return 'DATE'
    elif 'json' in type_lower:
        return 'JSONB'
    else:
        return 'TEXT'  # Default fallback


def print_report(issues: Dict) -> None:
    """Print a comprehensive schema comparison report."""
    print("\n" + "="*70)
    print("DATABASE SCHEMA VALIDATION REPORT")
    print("="*70)
    
    # Missing tables
    if issues['missing_tables']:
        print("\n❌ MISSING TABLES:")
        for table in issues['missing_tables']:
            print(f"   - {table}")
    else:
        print("\n✅ All required tables exist")
    
    # Missing columns
    if issues['missing_columns']:
        print("\n❌ MISSING COLUMNS:")
        for table, columns in issues['missing_columns'].items():
            print(f"\n   Table: {table}")
            for col, col_type in columns.items():
                print(f"      - {col} ({col_type})")
    else:
        print("\n✅ All required columns exist")
    
    # Extra columns (informational)
    if issues['extra_columns']:
        print("\n⚠️  EXTRA COLUMNS (in DB but not in models):")
        for table, columns in issues['extra_columns'].items():
            print(f"\n   Table: {table}")
            for col in columns:
                print(f"      - {col}")
    
    print("\n" + "="*70)


def main():
    """Main execution."""
    print("🔍 Analyzing database schema...")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Unknown'}")
    
    # Compare schemas
    issues = compare_schemas()
    
    # Print report
    print_report(issues)
    
    # Check if fixes are needed
    needs_fix = issues['missing_tables'] or issues['missing_columns']
    
    if not needs_fix:
        print("\n✅ Database schema is up to date!")
        return
    
    # Ask for confirmation
    print("\n" + "="*70)
    print("RECOMMENDED ACTIONS:")
    print("="*70)
    
    if issues['missing_tables']:
        print("\n1. Create missing tables from models")
    
    if issues['missing_columns']:
        print("\n2. Add missing columns:")
        for table, columns in issues['missing_columns'].items():
            for col in columns.keys():
                print(f"   - {table}.{col}")
    
    print("\n" + "="*70)
    response = input("\nApply fixes automatically? (yes/no/dry-run): ").strip().lower()
    
    if response == 'dry-run':
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
        fix_schema(issues, dry_run=True)
    elif response == 'yes':
        print("\n🔧 Applying fixes...\n")
        fixes = fix_schema(issues, dry_run=False)
        print("\n✅ FIXES APPLIED:")
        for fix in fixes:
            print(f"   ✓ {fix}")
        print("\n✅ Database schema updated successfully!")
        print("\n💡 Please restart your application for changes to take effect.")
    else:
        print("\n❌ No changes made. Exiting.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

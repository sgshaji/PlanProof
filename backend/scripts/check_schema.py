#!/usr/bin/env python3
"""Compare database schema with ORM models."""
import psycopg
from planproof.config import get_settings

settings = get_settings()
db_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

conn = psycopg.connect(db_url)
cursor = conn.cursor()

# Get all tables and their columns
cursor.execute("""
    SELECT 
        table_name,
        column_name,
        data_type,
        is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
""")

schema = {}
for row in cursor.fetchall():
    table_name, column_name, data_type, is_nullable = row
    if table_name not in schema:
        schema[table_name] = []
    schema[table_name].append({
        'column': column_name,
        'type': data_type,
        'nullable': is_nullable == 'YES'
    })

# Print schema
print("\n=== DATABASE SCHEMA ===\n")
for table_name in sorted(schema.keys()):
    print(f"\n## {table_name}")
    for col in schema[table_name]:
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  - {col['column']:<40} {col['type']:<20} {nullable}")

cursor.close()
conn.close()

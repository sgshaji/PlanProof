import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ["DATABASE_URL"]

DDL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
"""

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()

print("OK PostGIS extensions enabled")


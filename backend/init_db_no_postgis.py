#!/usr/bin/env python3
"""Initialize database without PostGIS-dependent tables."""
from planproof.db import Base, Database, GeometryFeature, SpatialMetric
from sqlalchemy import MetaData

# Remove PostGIS-dependent tables temporarily
Base.metadata.remove(GeometryFeature.__table__)
Base.metadata.remove(SpatialMetric.__table__)

db = Database()
db.create_tables()
print("✓ Tables created successfully (excluding PostGIS-dependent tables)")
print("✗ NOTE: geometry_features and spatial_metrics tables not created (PostGIS not available)")

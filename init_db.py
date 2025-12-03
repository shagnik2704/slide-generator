"""
Initialize the database by creating all tables.
Run this script once to set up the database.
"""
from database import engine, Base
from models import Project, Asset  # Import all models

# Create all tables
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully!")
print("   - projects")
print("   - assets")

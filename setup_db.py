"""
setup_db.py
-----------
Run this once to create all database tables.
Run from the project root: python setup_db.py
"""

from src.database.connection import engine, Base
from src.database import models  # this registers all table classes with Base

def setup():
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("✅ All tables created successfully")
    print("   Tables created:")
    print("   - meetings")
    print("   - action_items")
    print("   - decisions")
    print("   - audit_log")

if __name__ == "__main__":
    setup()
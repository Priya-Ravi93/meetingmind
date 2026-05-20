"""
connection.py
-------------
Manages the connection to our PostgreSQL database.
Every file that needs to save or read data imports from here.
Uses SQLAlchemy ORM - industry standard for enterprise applications.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found in .env file. "
        "Make sure your .env file exists and contains DATABASE_URL."
    )
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

class Base(DeclarativeBase):
    pass

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """
    Creates a database session and closes it when done.
    
    Use it like this in other files:
        with get_db() as db:
            db.add(something)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """
    Tests that we can actually connect to the database.
    Run this file directly to verify everything is working.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL successfully")
            print(f"   Version: {version}")
            return True
    except Exception as e:
        print(f"❌ Could not connect to PostgreSQL")
        print(f"   Error: {str(e)}")
        return False


if __name__ == "__main__":
    test_connection()
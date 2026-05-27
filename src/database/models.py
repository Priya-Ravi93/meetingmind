"""
models.py
---------
Defines all database tables as SQLAlchemy ORM classes.

Each class here becomes one table in PostgreSQL.
- Meeting      — one row per meeting the bot attended
- ActionItem   — one row per task extracted from a meeting
- Decision     — one row per decision made in a meeting
- AuditLog     — one row per action the bot took
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey , text
from sqlalchemy.sql import func
from src.database.connection import Base
from datetime import datetime

class Meeting(Base):
    """
    One row = one meeting the bot attended.
    All other tables link back to this one via meeting_id.
    """
    __tablename__ = "meetings"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    title            = Column(String(500), nullable=False)
    teams_meeting_id = Column(String(500), unique=True, nullable=True)
    organiser_name   = Column(String(200), nullable=True)
    organiser_email  = Column(String(200), nullable=True)
    started_at       = Column(DateTime, nullable=True)
    ended_at         = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    attendees        = Column(Text, nullable=True)
    missed_attendees = Column(Text, nullable=True)
    summary          = Column(Text, nullable=True)
    created_at       = Column(DateTime, server_default=func.now())

class ActionItem(Base):
    """
    One row = one action item extracted from a meeting.
    Links back to Meeting via meeting_id.
    """
    __tablename__ = "action_items"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id       = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    task             = Column(Text, nullable=False)
    owner            = Column(String(200), nullable=True)
    deadline         = Column(String(200), nullable=True)
    priority         = Column(String(50), nullable=True)
    status           = Column(String(50), default="open")
    jira_ticket_id   = Column(String(200), nullable=True)
    confidence_score = Column(Float, nullable=True)
    weeks_overdue    = Column(Integer, default=0)
    created_at       = Column(DateTime, server_default=func.now())

class Decision(Base):
    """
    One row = one decision made in a meeting.
    Links back to Meeting via meeting_id.
    """
    __tablename__ = "decisions"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    decision   = Column(Text, nullable=False)
    context    = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    """
    One row = one action the bot took.
    Full history of everything MeetingMind ever did.
    Enterprise audit trail.
    """
    __tablename__ = "audit_log"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id   = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    action       = Column(String(500), nullable=False)
    details      = Column(Text, nullable=True)
    performed_at = Column(DateTime, server_default=func.now())

def create_tables():
    """
    Creates all tables in PostgreSQL.
    Run this once to set up the database.
    SQLAlchemy reads every class that inherits from Base
    and generates the CREATE TABLE SQL automatically.
    """
    from src.database.connection import engine
    Base.metadata.create_all(engine)
    print("✅ All tables created successfully")
    print("   Tables: meetings, action_items, decisions, audit_log")

def save_meeting_results(
    meeting_title: str,
    summary,
    started_at=None,
    ended_at=None,
    organiser_name=None,
    organiser_email=None,
    attendees=None,
    missed_attendees=None,
    teams_meeting_id=None
):
    """
    Saves a complete meeting analysis to PostgreSQL.
    Saves meeting record, action items, decisions, and audit log
    all in one transaction — save all or save none.
    
    Args:
        meeting_title:    name of the meeting
        summary:          MeetingSummary object from extract.py
        started_at:       when meeting started
        ended_at:         when meeting ended
        organiser_name:   who organised the meeting
        organiser_email:  organiser email address
        attendees:        comma separated list of attendees
        missed_attendees: comma separated list of people who missed it
        teams_meeting_id: Microsoft Teams meeting ID
        
    Returns:
        meeting_id: the ID of the saved meeting record
    """
    from src.database.connection import SessionLocal
    
    db = SessionLocal()
    
    try:
        # ── Step 1: Save the meeting record ──────────────────────
        meeting = Meeting(
            title            = meeting_title,
            teams_meeting_id = teams_meeting_id,
            organiser_name   = organiser_name,
            organiser_email  = organiser_email,
            started_at       = started_at,
            ended_at         = ended_at,
            attendees        = attendees,
            missed_attendees = missed_attendees,
            summary          = summary.summary
        )
        db.add(meeting)
        db.flush()  # gets the auto-generated meeting ID without committing yet
        
        meeting_id = meeting.id
        print(f"   Meeting record created with ID: {meeting_id}")
        
        # ── Step 2: Save all action items ─────────────────────────
        for item in summary.action_items:
            action = ActionItem(
                meeting_id       = meeting_id,
                task             = item.task,
                owner            = item.owner,
                deadline         = item.deadline,
                priority         = item.priority,
                status           = "open",
                confidence_score = item.confidence_score
            )
            db.add(action)
        
        print(f"   {len(summary.action_items)} action items saved")
        
        # ── Step 3: Save all decisions ────────────────────────────
        for dec in summary.decisions:
            decision = Decision(
                meeting_id = meeting_id,
                decision   = dec.decision,
                context    = dec.context
            )
            db.add(decision)
        
        print(f"   {len(summary.decisions)} decisions saved")
        
        # ── Step 4: Save audit log entry ──────────────────────────
        log = AuditLog(
            meeting_id   = meeting_id,
            action       = "meeting_processed",
            details      = f"Extracted {len(summary.action_items)} action items and {len(summary.decisions)} decisions"
        )
        db.add(log)
        
        # ── Commit everything together — transaction complete ─────
        db.commit()
        print(f"✅ All data saved successfully — Meeting ID: {meeting_id}")
        
        return meeting_id
        
    except Exception as e:
        # Something went wrong — roll back everything
        # None of the above gets saved — save all or save none
        db.rollback()
        print(f"❌ Save failed — rolling back all changes")
        print(f"   Error: {str(e)}")
        raise
        
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
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

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.sql import func
from src.database.connection import Base

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
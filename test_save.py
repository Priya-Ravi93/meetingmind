"""
test_save.py
------------
Tests the complete pipeline:
1. Extract from transcript using Ollama
2. Save results to PostgreSQL
3. Verify data was saved correctly
"""

from src.agents.extract import extract_from_transcript
from src.database.models import save_meeting_results

# The same test transcript from before
test_transcript = """
Sarah: OK everyone let's get started. John can you give us 
       the update on the login bug?

John: Yeah so we found the root cause yesterday. 
      It's a session timeout issue. I'll have a fix ready by Thursday.

Sarah: Great. Maria what's the status on the new dashboard?

Maria: Still in progress. I need the API specs from John 
       before I can finish. John can you send those over today?

John: Yes I'll send them this afternoon.

Sarah: Perfect. We've also decided to push the release date 
       to the 20th. Everyone agreed on that in the thread yesterday.
       Next meeting is Friday at 2pm. Any other actions?

Maria: I need to update the documentation once John's fix is merged.

Sarah: OK add that to the list. Thanks everyone.
"""

print("=" * 50)
print("Step 1 — Extracting from transcript...")
print("=" * 50)

result = extract_from_transcript(test_transcript)

print(f"✅ Extraction complete")
print(f"   Action items found: {len(result.action_items)}")
print(f"   Decisions found: {len(result.decisions)}")
print()

print("=" * 50)
print("Step 2 — Saving to PostgreSQL...")
print("=" * 50)

meeting_id = save_meeting_results(
    meeting_title    = "Sprint Planning",
    summary          = result,
    organiser_name   = "Sarah Chen",
    organiser_email  = "sarah@company.com",
    attendees        = "Sarah Chen, John Smith, Maria Patel",
    missed_attendees = "Alex Johnson"
)

print()
print("=" * 50)
print("Step 3 — Verifying data in PostgreSQL...")
print("=" * 50)

# Verify by reading back from database
from src.database.connection import SessionLocal
from src.database.models import Meeting, ActionItem, Decision, AuditLog

db = SessionLocal()

meeting  = db.query(Meeting).filter(Meeting.id == meeting_id).first()
actions  = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
logs     = db.query(AuditLog).filter(AuditLog.meeting_id == meeting_id).all()

print(f"Meeting: {meeting.title}")
print(f"Organiser: {meeting.organiser_name}")
print(f"Summary: {meeting.summary[:80]}...")
print()
print(f"Action items in database ({len(actions)}):")
for a in actions:
    print(f"  - {a.task} | {a.owner} | {a.deadline} | {a.priority} | {a.status}")
print()
print(f"Decisions in database ({len(decisions)}):")
for d in decisions:
    print(f"  - {d.decision}")
print()
print(f"Audit log ({len(logs)} entries):")
for l in logs:
    print(f"  - {l.action}: {l.details}")

db.close()

print()
print("✅ Complete pipeline working — extract → save → verify")
"""
memory.py
---------
The memory node - checks database for carry-overs from previous meetings.

What it does:
1. Looks at current action items extracted from today's meeting
2. Searches database for same owners from previous meetings
3. Finds action items that were assigned before but never completed
4. Adds carry-over warnings to the state

Example output:
⚠️ Carried over 2 weeks: John — Fix login bug — still open
⚠️ Carried over 1 week: Maria — Update documentation — still open
"""
from typing import List, Optional
from pydantic import BaseModel
from src.database.connection import SessionLocal
from src.database.models import ActionItem as ActionItemDB

class CarryOver(BaseModel):
    """
    Represents one action item carried over from a previous meeting.
    Was assigned before but never marked as complete.
    """
    task:          str
    owner:         Optional[str] = None
    weeks_overdue: int           = 1
    original_meeting_id: int

def check_carry_overs(action_items: List) -> List[CarryOver]:
    """
    Checks database for incomplete action items from previous meetings.
    
    Args:
        action_items: list of ActionItem objects from today's meeting
        
    Returns:
        list of CarryOver objects — items never completed from before
    """
    db = SessionLocal()
    carry_overs = []
    
    try:
        # Get all owners from today's meeting
        todays_owners = [
            item.owner 
            for item in action_items 
            if item.owner is not None
        ]
        
        if not todays_owners:
            return []
        
        # Search database for open items assigned to same owners
        previous_items = db.query(ActionItemDB).filter(
            ActionItemDB.owner.in_(todays_owners),
            ActionItemDB.status == "open"
        ).all()
        
        # Convert to CarryOver objects
        for item in previous_items:
            carry_over = CarryOver(
                task                = item.task,
                owner               = item.owner,
                weeks_overdue       = item.weeks_overdue or 1,
                original_meeting_id = item.meeting_id
            )
            carry_overs.append(carry_over)
        
        return carry_overs
        
    except Exception as e:
        print(f"Memory check failed: {str(e)}")
        return []
        
    finally:
        db.close()


if __name__ == "__main__":
    # Test with fake action items
    from src.agents.extract import ActionItem
    
    test_items = [
        ActionItem(task="Fix login bug", owner="John", deadline="Friday"),
        ActionItem(task="Send API docs", owner="Sarah", deadline="Today"),
    ]
    
    print("Checking for carry-overs...")
    carry_overs = check_carry_overs(test_items)
    
    if carry_overs:
        print(f"Found {len(carry_overs)} carry-over(s):")
        for co in carry_overs:
            print(f"  ⚠️ {co.weeks_overdue} week(s): {co.owner} — {co.task}")
    else:
        print("No carry-overs found")
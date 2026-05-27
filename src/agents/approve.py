"""
approve.py
----------
The human-in-the-loop approval node.

What it does:
1. Formats the extracted action items and carry-overs
2. Sends an approval request to the meeting organiser
3. Pauses the LangGraph pipeline — saves state to database
4. Waits for organiser to approve or reject each item
5. Resumes only after approval received

This node ensures the bot never takes irreversible actions
without explicit human confirmation.
Enterprise requirement — AI never acts autonomously
on consequential decisions.
"""

from typing import List, Optional
from pydantic import BaseModel

class ApprovalRequest(BaseModel):
    """
    Everything presented to the organiser for approval.
    Sent as a Teams message before any actions are taken.
    """
    meeting_title:  str
    summary:        str
    action_items:   List[dict]
    carry_overs:    List[dict]
    decisions:      List[dict]
    next_meeting:   Optional[str] = None

def format_approval_request(
    meeting_title: str,
    summary,
    carry_overs: List
) -> ApprovalRequest:
    """
    Formats extracted meeting data into an approval request.
    This is what gets sent to the organiser before any actions.
    
    Args:
        meeting_title: name of the meeting
        summary:       MeetingSummary object from extract.py
        carry_overs:   list of CarryOver objects from memory.py
        
    Returns:
        ApprovalRequest object ready to send to organiser
    """
    
    # Format action items as simple dictionaries
    action_items = [
        {
            "task":     item.task,
            "owner":    item.owner or "Unassigned",
            "deadline": item.deadline or "No deadline",
            "priority": item.priority or "Medium"
        }
        for item in summary.action_items
    ]
    
    # Format carry-overs as simple dictionaries
    formatted_carry_overs = [
        {
            "task":          co.task,
            "owner":         co.owner or "Unassigned",
            "weeks_overdue": co.weeks_overdue
        }
        for co in carry_overs
    ]
    
    # Format decisions as simple dictionaries
    decisions = [
        {
            "decision": dec.decision,
            "context":  dec.context or ""
        }
        for dec in summary.decisions
    ]
    
    return ApprovalRequest(
        meeting_title = meeting_title,
        summary       = summary.summary,
        action_items  = action_items,
        carry_overs   = formatted_carry_overs,
        decisions     = decisions,
        next_meeting  = summary.next_meeting
    )


def format_teams_message(approval: ApprovalRequest) -> str:
    """
    Converts an ApprovalRequest into a formatted Teams message.
    This is the actual text posted to the Teams meeting chat.
    """
    
    lines = []
    
    # Header
    lines.append(f"🤖 **MeetingMind — {approval.meeting_title}**")
    lines.append("")
    
    # Summary
    lines.append("📋 **SUMMARY**")
    lines.append(approval.summary)
    lines.append("")
    
    # Action items
    lines.append(f"✅ **ACTION ITEMS ({len(approval.action_items)} found)**")
    for i, item in enumerate(approval.action_items, 1):
        lines.append(
            f"{i}. **{item['owner']}** — {item['task']} "
            f"| Due: {item['deadline']} | {item['priority']} priority"
        )
    lines.append("")
    
    # Carry-overs
    if approval.carry_overs:
        lines.append(f"⚠️ **CARRY-OVERS FROM PREVIOUS MEETINGS**")
        for co in approval.carry_overs:
            lines.append(
                f"• {co['owner']} — {co['task']} "
                f"({co['weeks_overdue']} week(s) overdue)"
            )
        lines.append("")
    
    # Decisions
    if approval.decisions:
        lines.append(f"🏁 **DECISIONS MADE**")
        for dec in approval.decisions:
            lines.append(f"• {dec['decision']}")
        lines.append("")
    
    # Next meeting
    if approval.next_meeting:
        lines.append(f"📅 **NEXT MEETING:** {approval.next_meeting}")
        lines.append("")
    
    # Approval instruction
    lines.append("---")
    lines.append(
        "Please reply with the numbers of action items to approve. "
        "Example: **1,2,3** to approve all. "
        "Or **1,3** to approve only items 1 and 3."
    )
    
    return "\n".join(lines)

if __name__ == "__main__":
    from src.agents.extract import extract_from_transcript
    from src.agents.memory import check_carry_overs

    test_transcript = """
    Sarah: OK let's get started. John can you give us 
           the update on the login bug?
    
    John: Yeah I'll have a fix ready by Thursday.
    
    Sarah: Great. Maria what's the status on the dashboard?
    
    Maria: Still in progress. I need API specs from John today.
    
    John: I'll send them this afternoon.
    
    Sarah: We've decided to push the release to the 20th.
           Next meeting is Friday at 2pm.
    """

    print("Step 1 — Extracting from transcript...")
    summary = extract_from_transcript(test_transcript)

    print("Step 2 — Checking carry-overs...")
    carry_overs = check_carry_overs(summary.action_items)

    print("Step 3 — Formatting approval request...")
    approval = format_approval_request(
        meeting_title = "Sprint Planning",
        summary       = summary,
        carry_overs   = carry_overs
    )

    print("Step 4 — Formatting Teams message...")
    message = format_teams_message(approval)

    print()
    print("=" * 60)
    print("TEAMS MESSAGE THAT WOULD BE SENT TO ORGANISER:")
    print("=" * 60)
    print(message)
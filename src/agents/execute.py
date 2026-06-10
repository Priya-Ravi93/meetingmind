"""
execute.py
----------
The execution node - takes approved items and acts on them.

What it does:
1. Saves meeting and approved items to PostgreSQL
2. Creates Jira tickets for approved action items
3. Posts formatted summary to Teams meeting chat
4. Sends personal messages to missed attendees

This node only runs AFTER human approval.
Nothing irreversible happens before this point.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv
from src.database.models import save_meeting_results
from src.agents.approve import ApprovalRequest

load_dotenv()

def create_jira_ticket(item: dict) -> str:
    """
    Creates one Jira ticket for an approved action item.
    
    Args:
        item: dictionary with task, owner, deadline, priority
        
    Returns:
        Jira ticket ID e.g. "PROJ-123"
        
    Note:
        Currently a stub — returns simulated ticket ID.
        Will be replaced with real Jira REST API or MCP in Phase 2.
    """
    jira_base_url   = os.getenv("JIRA_BASE_URL")
    jira_email      = os.getenv("JIRA_EMAIL")
    jira_api_token  = os.getenv("JIRA_API_TOKEN")
    jira_project    = os.getenv("JIRA_PROJECT_KEY", "PROJ")
    
    # For now — simulate ticket creation
    # Real Jira REST API call goes here in Phase 2
    # When we add MCP — this entire function gets replaced
    
    print(f"   [JIRA STUB] Would create ticket:")
    print(f"   Title: {item['task']}")
    print(f"   Assignee: {item['owner']}")
    print(f"   Due: {item['deadline']}")
    print(f"   Priority: {item['priority']}")
    
    # Return simulated ticket ID
    import random
    ticket_id = f"{jira_project}-{random.randint(100, 999)}"
    return ticket_id

def post_teams_summary(
    approval:       ApprovalRequest,
    approved_items: List[dict]
) -> bool:
    """
    Posts the meeting summary to Teams meeting chat.
    
    Args:
        approval:       the ApprovalRequest with meeting details
        approved_items: only the approved action items
        
    Returns:
        True if posted successfully, False if failed
        
    Note:
        Currently a stub — prints what would be posted.
        Real Microsoft Graph API call goes here in Phase 2.
    """
    
    # Build the summary message
    lines = []
    
    # Header
    lines.append(f"🤖 MeetingMind — {approval.meeting_title}")
    lines.append("")
    
    # Summary
    lines.append("📋 SUMMARY")
    lines.append(approval.summary)
    lines.append("")
    
    # Approved action items only
    lines.append(f"✅ ACTION ITEMS ({len(approved_items)} approved)")
    for i, item in enumerate(approved_items, 1):
        lines.append(
            f"{i}. @{item['owner']} — {item['task']} "
            f"| Due: {item['deadline']} | {item['priority']}"
        )
    lines.append("")
    
    # Decisions
    if approval.decisions:
        lines.append("🏁 DECISIONS")
        for dec in approval.decisions:
            lines.append(f"• {dec['decision']}")
        lines.append("")
    
    # Next meeting
    if approval.next_meeting:
        lines.append(f"📅 NEXT MEETING: {approval.next_meeting}")
        lines.append("")
    
    message = "\n".join(lines)
    
    # Stub — print instead of posting to Teams
    print(f"   [TEAMS STUB] Would post to meeting chat:")
    print("   " + "-" * 40)
    for line in lines:
        print(f"   {line}")
    print("   " + "-" * 40)
    
    return True


def notify_missed_attendees(
    approval:         ApprovalRequest,
    missed_attendees: str
) -> bool:
    """
    Sends personal Teams messages to people who missed the meeting.
    
    Args:
        approval:         the ApprovalRequest with meeting details
        missed_attendees: comma separated string of names/emails
                         e.g. "Alex Johnson, Tom Smith"
        
    Returns:
        True if notifications sent, False if failed
        
    Note:
        Currently a stub — prints what would be sent.
        Real Microsoft Graph API call goes here in Phase 2.
    """
    
    # Split comma separated string into individual names
    missed_list = [
        person.strip() 
        for person in missed_attendees.split(",")
        if person.strip()
    ]
    
    if not missed_list:
        print("   No missed attendees to notify")
        return True
    
    for person in missed_list:
        
        # Find action items assigned to this person
        their_items = [
            item for item in approval.action_items
            if item.get("owner", "").lower() == person.lower()
        ]
        
        # Build personal message
        lines = []
        lines.append(f"Hi {person} — you missed the {approval.meeting_title} meeting.")
        lines.append("")
        lines.append("Here is what was discussed:")
        lines.append(approval.summary)
        lines.append("")
        
        # Their specific action items
        if their_items:
            lines.append(f"YOUR ACTION ITEMS ({len(their_items)}):")
            for item in their_items:
                lines.append(
                    f"• {item['task']} "
                    f"| Due: {item['deadline']} "
                    f"| Priority: {item['priority']}"
                )
        else:
            lines.append("No action items assigned to you this time.")
        
        lines.append("")
        
        # Decisions
        if approval.decisions:
            lines.append("DECISIONS MADE:")
            for dec in approval.decisions:
                lines.append(f"• {dec['decision']}")
            lines.append("")
        
        # Next meeting
        if approval.next_meeting:
            lines.append(f"NEXT MEETING: {approval.next_meeting}")
        
        message = "\n".join(lines)
        
        # Stub — print instead of sending real Teams message
        print(f"   [TEAMS STUB] Would send personal message to {person}:")
        print("   " + "-" * 40)
        for line in lines:
            print(f"   {line}")
        print("   " + "-" * 40)
        print()
    
    return True

def execute_approved_actions(
    approval:         ApprovalRequest,
    approved_indices: List[int]
) -> dict:
    """
    Executes all approved actions after human confirmation.
    Calls each helper function in sequence.
    Returns results of every action taken.
    
    Args:
        approval:         ApprovalRequest from approve.py
        approved_indices: item numbers organiser approved
                         e.g. [1, 2] means items 1 and 2
        
    Returns:
        dict showing what succeeded and what failed
    """
    
    print(f"\n{'='*50}")
    print(f"Executing approved actions...")
    print(f"{'='*50}")
    
    results = {
        "meeting_id":      None,
        "jira_tickets":    [],
        "teams_posted":    False,
        "missed_notified": False,
        "errors":          []
    }
    
    # ── Step 1: Filter approved items ────────────────────────────
    # approved_indices is 1-based (human friendly: "approve items 1,2,3")
    # Python lists are 0-based so we subtract 1
    approved_items = []
    for i in approved_indices:
        index = i - 1
        if 0 <= index < len(approval.action_items):
            approved_items.append(approval.action_items[index])
    
    print(f"\n{len(approved_items)} of {len(approval.action_items)} items approved")
    
    # ── Step 2: Save to PostgreSQL ────────────────────────────────
    try:
        from src.agents.extract import MeetingSummary
        from src.agents.extract import ActionItem as PydanticActionItem
        from src.agents.extract import Decision as PydanticDecision
        
        action_items = [
            PydanticActionItem(
                task     = item["task"],
                owner    = item["owner"],
                deadline = item["deadline"],
                priority = item["priority"]
            )
            for item in approved_items
        ]
        
        decisions = [
            PydanticDecision(
                decision = dec["decision"],
                context  = dec.get("context", "")
            )
            for dec in approval.decisions
        ]
        
        summary_obj = MeetingSummary(
            action_items = action_items,
            decisions    = decisions,
            summary      = approval.summary,
            next_meeting = approval.next_meeting
        )
        
        meeting_id = save_meeting_results(
            meeting_title    = approval.meeting_title,
            summary          = summary_obj,
            organiser_name   = approval.organiser_name,
            organiser_email  = approval.organiser_email,
            attendees        = approval.attendees,
            missed_attendees = approval.missed_attendees,
            teams_meeting_id = approval.teams_meeting_id
        )
        
        results["meeting_id"] = meeting_id
        print(f"\n✅ Saved to database — Meeting ID: {meeting_id}")
        
    except Exception as e:
        error = f"Database save failed: {str(e)}"
        results["errors"].append(error)
        print(f"\n❌ {error}")
    
    # ── Step 3: Create Jira tickets if enabled ────────────────────
    jira_enabled = os.getenv("JIRA_ENABLED", "false").lower() == "true"
    
    if jira_enabled:
        print("\nCreating Jira tickets...")
        for item in approved_items:
            try:
                ticket_id = create_jira_ticket(item)
                results["jira_tickets"].append(ticket_id)
                print(f"✅ Created: {ticket_id}")
            except Exception as e:
                error = f"Jira failed for '{item['task']}': {str(e)}"
                results["errors"].append(error)
                print(f"❌ {error}")
    else:
        print("\n⏭️  Jira disabled — skipping")
    
    # ── Step 4: Post to Teams ─────────────────────────────────────
    teams_enabled = os.getenv(
        "TEAMS_POSTING_ENABLED", "true"
    ).lower() == "true"
    
    if teams_enabled:
        try:
            post_teams_summary(approval, approved_items)
            results["teams_posted"] = True
        except Exception as e:
            error = f"Teams posting failed: {str(e)}"
            results["errors"].append(error)
            print(f"❌ {error}")
    else:
        print("\n⏭️  Teams posting disabled — skipping")
    
    # ── Step 5: Notify missed attendees ───────────────────────────
    if approval.missed_attendees:
        try:
            notify_missed_attendees(approval, approval.missed_attendees)
            results["missed_notified"] = True
        except Exception as e:
            error = f"Missed attendee notification failed: {str(e)}"
            results["errors"].append(error)
            print(f"❌ {error}")
    
    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"Execution complete")
    print(f"  Meeting ID:    {results['meeting_id']}")
    print(f"  Jira tickets:  {results['jira_tickets']}")
    print(f"  Teams posted:  {results['teams_posted']}")
    print(f"  Missed notified: {results['missed_notified']}")
    if results["errors"]:
        print(f"  Errors: {results['errors']}")
    print(f"{'='*50}\n")
    
    return results

if __name__ == "__main__":
    from src.agents.extract import extract_from_transcript
    from src.agents.memory import check_carry_overs
    from src.agents.approve import format_approval_request

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

    print("Step 1 — Extracting...")
    summary = extract_from_transcript(test_transcript)

    print("Step 2 — Checking carry-overs...")
    carry_overs = check_carry_overs(summary.action_items)

    print("Step 3 — Formatting approval request...")
    approval = format_approval_request(
        meeting_title    = "Sprint Planning",
        summary          = summary,
        carry_overs      = carry_overs,
        organiser_name   = "Sarah Chen",
        organiser_email  = "sarah@company.com",
        attendees        = "Sarah Chen, John Smith, Maria Patel",
        missed_attendees = "Alex Johnson"
    )

    print("Step 4 — Simulating organiser approves items 1 and 2...")
    approved_indices = [1, 2]

    print("Step 5 — Executing approved actions...")
    results = execute_approved_actions(
        approval         = approval,
        approved_indices = approved_indices
    )

    print("Final results:")
    print(results)
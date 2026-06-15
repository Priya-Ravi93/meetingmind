"""
pipeline.py
-----------
The LangGraph pipeline - connects all four nodes into
a stateful workflow.

Graph structure:
START → extract → memory → approve → execute → END
                              ↑
                         INTERRUPT HERE
                    (waits for human approval)

The state is a shared dictionary that travels through
every node. Each node reads from it and writes to it.
"""

import os
from typing import TypedDict, List, Optional, Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.agents.extract import extract_from_transcript
from src.agents.memory import check_carry_overs
from src.agents.approve import format_approval_request, format_teams_message
from src.agents.execute import execute_approved_actions

load_dotenv()

class MeetingState(TypedDict):
    """
    The shared state that travels through every node.
    Each node reads from it and writes to it.
    Think of it as the folder passed between workers.
    """
    # Input — provided when pipeline starts
    transcript:       str
    meeting_title:    str
    organiser_name:   Optional[str]
    organiser_email:  Optional[str]
    attendees:        Optional[str]
    missed_attendees: Optional[str]
    teams_meeting_id: Optional[str]
    
    # Filled by extract_node
    action_items:     Optional[list]
    decisions:        Optional[list]
    summary_text:     Optional[str]
    next_meeting:     Optional[str]
    
    # Filled by memory_node
    carry_overs:      Optional[list]
    
    # Filled by approve_node
    approval:         Optional[dict]
    teams_message:    Optional[str]
    
    # Filled by human — triggers execute_node
    approved_indices: Optional[List[int]]
    
    # Filled by execute_node
    results:          Optional[dict]
    
    # Error tracking
    error:            Optional[str]

def extract_node(state: MeetingState) -> MeetingState:
    """
    Reads transcript from state.
    Calls extract_from_transcript().
    Writes action items, decisions, summary back to state.
    """
    print("\n[EXTRACT NODE] Reading transcript...")
    
    try:
        transcript = state["transcript"]
        
        # Call the agent function
        result = extract_from_transcript(transcript)
        
        # Write results back to state
        return {
            **state,
            "action_items": [item.model_dump() for item in result.action_items],
            "decisions":    [dec.model_dump() for dec in result.decisions],
            "summary_text": result.summary,
            "next_meeting": result.next_meeting,
            "error":        None
        }
        
    except Exception as e:
        print(f"[EXTRACT NODE] Error: {str(e)}")
        return {**state, "error": str(e)}
    

# ── Node 2: Memory ────────────────────────────────────────────────
def memory_node(state: MeetingState) -> MeetingState:
    """
    Reads action items from state.
    Calls check_carry_overs().
    Writes carry-overs back to state.
    """
    print("\n[MEMORY NODE] Checking carry-overs...")
    
    try:
        action_items = state.get("action_items", [])
        
        if not action_items:
            print("[MEMORY NODE] No action items to check")
            return {**state, "carry_overs": []}
        
        # Convert dictionaries back to ActionItem objects
        # check_carry_overs() expects ActionItem objects not dicts
        from src.agents.extract import ActionItem
        action_item_objects = [
            ActionItem(**item) for item in action_items
        ]
        
        # Call the agent function
        carry_overs = check_carry_overs(action_item_objects)
        
        # Write results back to state
        return {
            **state,
            "carry_overs": [co.model_dump() for co in carry_overs],
            "error":       None
        }
        
    except Exception as e:
        print(f"[MEMORY NODE] Error: {str(e)}")
        return {**state, "carry_overs": [], "error": str(e)}
    
# ── Node 3: Approve ───────────────────────────────────────────────
def approve_node(state: MeetingState) -> MeetingState:
    """
    Reads action items, carry-overs, decisions from state.
    Formats approval request and Teams message.
    Writes approval object back to state.
    This node triggers the interrupt — graph pauses here.
    """
    print("\n[APPROVE NODE] Formatting approval request...")
    
    try:
        # Get everything from state
        from src.agents.extract import MeetingSummary, ActionItem, Decision
        
        action_items = [
            ActionItem(**item) 
            for item in state.get("action_items", [])
        ]
        
        decisions = [
            Decision(**dec) 
            for dec in state.get("decisions", [])
        ]
        
        from src.agents.extract import MeetingSummary
        summary_obj = MeetingSummary(
            action_items = action_items,
            decisions    = decisions,
            summary      = state.get("summary_text", ""),
            next_meeting = state.get("next_meeting")
        )
        
        carry_overs_raw = state.get("carry_overs", [])
        from src.agents.memory import CarryOver
        carry_over_objects = [
            CarryOver(**co) for co in carry_overs_raw
        ]
        
        # Format the approval request
        approval = format_approval_request(
            meeting_title    = state.get("meeting_title", "Meeting"),
            summary          = summary_obj,
            carry_overs      = carry_over_objects,
            organiser_name   = state.get("organiser_name"),
            organiser_email  = state.get("organiser_email"),
            attendees        = state.get("attendees"),
            missed_attendees = state.get("missed_attendees"),
            teams_meeting_id = state.get("teams_meeting_id")
        )
        
        # Format the Teams message
        teams_message = format_teams_message(approval)
        
        print("[APPROVE NODE] Approval request ready")
        print("[APPROVE NODE] Waiting for human approval...")
        print("\n" + "="*60)
        print("TEAMS MESSAGE READY TO SEND:")
        print("="*60)
        print(teams_message)
        print("="*60)
        
        return {
            **state,
            "approval": approval.model_dump(),
            "teams_message": teams_message,
            "error":         None
        }
        
    except Exception as e:
        print(f"[APPROVE NODE] Error: {str(e)}")
        return {**state, "error": str(e)}
    
# ── Node 4: Execute ───────────────────────────────────────────────
def execute_node(state: MeetingState) -> MeetingState:
    """
    Reads approved_indices from state.
    Calls execute_approved_actions().
    Writes results back to state.
    This node runs AFTER human approval.
    """
    print("\n[EXECUTE NODE] Executing approved actions...")
    
    try:
        # Get approved indices from state
        # These were set by the human after reviewing
        approved_indices = state.get("approved_indices", [])
        
        if not approved_indices:
            print("[EXECUTE NODE] No items approved — nothing to execute")
            return {**state, "results": {}, "error": None}
        
        # Get the approval object from state
        from src.agents.approve import ApprovalRequest
        approval_dict = state.get("approval", {})
        approval = ApprovalRequest(**approval_dict)
        
        # Call the agent function
        results = execute_approved_actions(
            approval         = approval,
            approved_indices = approved_indices
        )
        
        # Write results back to state
        return {
            **state,
            "results": results,
            "error":   None
        }
        
    except Exception as e:
        print(f"[EXECUTE NODE] Error: {str(e)}")
        return {**state, "error": str(e)}
    
# ── Build the graph ───────────────────────────────────────────────
def build_graph():
    """
    Builds and compiles the LangGraph workflow.
    
    Graph structure:
    START → extract → memory → approve → execute → END
                                  ↑
                             INTERRUPT HERE
    
    Returns:
        Compiled graph ready to run
    """
    
    # Create a new graph using MeetingState as the state shape
    graph = StateGraph(MeetingState)
    
    # ── Add all four nodes ────────────────────────────────────────
    graph.add_node("extract", extract_node)
    graph.add_node("memory",  memory_node)
    graph.add_node("approve", approve_node)
    graph.add_node("execute", execute_node)
    
    # ── Add edges — define the flow ───────────────────────────────
    graph.add_edge(START,     "extract")
    graph.add_edge("extract", "memory")
    graph.add_edge("memory",  "approve")
    graph.add_edge("approve", "execute")
    graph.add_edge("execute", END)
    
    # ── Set the interrupt ─────────────────────────────────────────
    # Graph pauses BEFORE approve node
    # Waits for human to set approved_indices in state
    # Then resumes and runs approve → execute
    
    # ── Compile with memory checkpoint ───────────────────────────
    # MemorySaver stores state when graph pauses at interrupt
    # In production replace with PostgreSQL checkpointer
    memory = MemorySaver()
    
    compiled = graph.compile(
        checkpointer     = memory,
        interrupt_before = ["approve"]
    )
    
    return compiled


# Create one instance of the graph
meeting_graph = build_graph()

# ── Public functions ──────────────────────────────────────────────

def run_pipeline(
    transcript:       str,
    meeting_title:    str,
    organiser_name:   str  = None,
    organiser_email:  str  = None,
    attendees:        str  = None,
    missed_attendees: str  = None,
    teams_meeting_id: str  = None
) -> dict:
    """
    Starts the pipeline with a transcript.
    Runs extract → memory → pauses before approve.
    
    Returns the thread_id needed to resume after approval.
    
    Args:
        transcript:    raw meeting transcript
        meeting_title: name of the meeting
        
    Returns:
        dict with thread_id and current state
    """
    
    # Each run needs a unique thread ID
    # In production this comes from the Teams meeting ID
    import uuid
    thread_id = teams_meeting_id or str(uuid.uuid4())
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initial state
    initial_state = {
        "transcript":       transcript,
        "meeting_title":    meeting_title,
        "organiser_name":   organiser_name,
        "organiser_email":  organiser_email,
        "attendees":        attendees,
        "missed_attendees": missed_attendees,
        "teams_meeting_id": teams_meeting_id,
        "action_items":     None,
        "decisions":        None,
        "summary_text":     None,
        "next_meeting":     None,
        "carry_overs":      None,
        "approval":         None,
        "teams_message":    None,
        "approved_indices": None,
        "results":          None,
        "error":            None
    }
    
    print(f"\n{'='*60}")
    print(f"Starting MeetingMind pipeline")
    print(f"Meeting: {meeting_title}")
    print(f"Thread ID: {thread_id}")
    print(f"{'='*60}")
    
    # Run the graph — it will pause before approve node
    meeting_graph.invoke(initial_state, config)
    
    # Get the current state after pausing
    current_state = meeting_graph.get_state(config)
    
    return {
        "thread_id":    thread_id,
        "state":        current_state.values,
        "next":         current_state.next
    }


def resume_pipeline(
    thread_id:        str,
    approved_indices: List[int]
) -> dict:
    """
    Resumes the pipeline after human approval.
    Updates state with approved indices.
    Runs approve → execute.
    
    Args:
        thread_id:        from run_pipeline() return value
        approved_indices: list of approved item numbers e.g. [1, 2]
        
    Returns:
        final results dict
    """
    
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"\n{'='*60}")
    print(f"Resuming pipeline — Thread: {thread_id}")
    print(f"Approved items: {approved_indices}")
    print(f"{'='*60}")
    
    # Update state with human's approval decision
    meeting_graph.update_state(
        config,
        {"approved_indices": approved_indices}
    )
    
    # Resume the graph from where it paused
    meeting_graph.invoke(None, config)
    
    # Get the final state
    final_state = meeting_graph.get_state(config)
    
    return final_state.values.get("results", {})




if __name__ == "__main__":
    
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
    
    # ── Stage 1: Run pipeline until it pauses ─────────────────────
    print("STAGE 1 — Starting pipeline...")
    result = run_pipeline(
        transcript       = test_transcript,
        meeting_title    = "Sprint Planning",
        organiser_name   = "Sarah Chen",
        organiser_email  = "sarah@company.com",
        attendees        = "Sarah Chen, John Smith, Maria Patel",
        missed_attendees = "Alex Johnson"
    )
    
    thread_id = result["thread_id"]
    
    # Show the current state
    state = result["state"]
    action_items = state.get("action_items", [])
    
    print(f"\n{'='*60}")
    print("PIPELINE PAUSED — Waiting for your approval")
    print(f"{'='*60}")
    print(f"\nAction items found ({len(action_items)}):")
    for i, item in enumerate(action_items, 1):
        print(f"  {i}. {item['owner']} — {item['task']}")
        print(f"     Deadline: {item['deadline']} | Priority: {item['priority']}")
    
    print(f"\nCarry-overs from previous meetings:")
    carry_overs = state.get("carry_overs", [])
    if carry_overs:
        for co in carry_overs:
            print(f"  ⚠️  {co['owner']} — {co['task']} ({co['weeks_overdue']} week(s))")
    else:
        print("  None")
    
    print(f"\nDecisions made:")
    decisions = state.get("decisions", [])
    for dec in decisions:
        print(f"  • {dec['decision']}")
    
    # ── Wait for real human input ──────────────────────────────────
    print(f"\n{'='*60}")
    print("YOUR TURN — Review the action items above")
    print("Enter the numbers you want to approve")
    print(f"There are {len(action_items)} action items")
    print("Example: 1,2  to approve items 1 and 2")
    print("Example: 1    to approve only item 1")
    print(f"Example: 1,2  to approve all (if 2 items)")
    print(f"{'='*60}")
    
    user_input = input("\nEnter approved item numbers: ")
    
    # Parse the input
    try:
        approved_indices = [
            int(x.strip()) 
            for x in user_input.split(",")
            if x.strip().isdigit()
        ]
    except:
        approved_indices = []
    
    if not approved_indices:
        print("No valid numbers entered. Exiting.")
        exit()
    
    # Warn about invalid numbers
    max_items = len(action_items)
    invalid = [i for i in approved_indices if i > max_items]
    if invalid:
        print(f"⚠️  Items {invalid} do not exist — only {max_items} items available. Ignoring.")
        approved_indices = [i for i in approved_indices if i <= max_items]
    
    if not approved_indices:
        print("No valid items remaining after filtering. Exiting.")
        exit()
    
    print(f"\nYou approved items: {approved_indices}")
    
    # ── Stage 2: Resume after your approval ───────────────────────
    print("\nSTAGE 2 — Resuming pipeline with your approval...")
    final_results = resume_pipeline(
        thread_id        = thread_id,
        approved_indices = approved_indices
    )
    
    print("\nFINAL RESULTS:")
    print(f"  Meeting saved with ID: {final_results.get('meeting_id')}")
    print(f"  Jira tickets: {final_results.get('jira_tickets')}")
    print(f"  Teams posted: {final_results.get('teams_posted')}")
    print(f"  Missed attendees notified: {final_results.get('missed_notified')}")
    print(f"  Errors: {final_results.get('errors')}")
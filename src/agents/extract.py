"""
extract.py
----------
The AI extraction agent - the core intelligence of MeetingMind.

Does two things:
1. Defines Pydantic models - the exact shape of AI output
2. extract_from_transcript() - sends transcript to Ollama,
   validates the response, returns structured data

This is the first node in the LangGraph pipeline.
"""
import json
import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

class ActionItem(BaseModel):
    """
    Represents one action item extracted from a meeting.
    One instance = one task someone needs to do.
    """
    task:             str
    owner:            Optional[str] = None
    deadline:         Optional[str] = None
    priority:         Optional[str] = None
    confidence_score: Optional[float] = None

class Decision(BaseModel):
    """
    Represents one decision made during a meeting.
    One instance = one thing the team agreed on.
    """
    decision: str
    context:  Optional[str] = None

class MeetingSummary(BaseModel):
    """
    The complete output from analysing one meeting.
    Contains all action items, decisions, summary and next meeting.
    This is what the AI returns after reading the full transcript.
    """
    action_items: List[ActionItem]
    decisions:    List[Decision]
    summary:      str
    next_meeting: Optional[str] = None

# ── Connect to local Ollama AI ────────────────────────────────────
# ChatOllama connects to Ollama running on my mac
# temperature=0.0 means consistent, factual responses every time
# No internet needed - runs entirely on machine

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "llama3.2"),
    temperature=0.0
)

# ── The prompt template ───────────────────────────────────────────
# This is the instruction we send to the AI along with the transcript.
# The quality of this prompt directly determines the quality of extraction.
# Clear, specific instructions = reliable structured output.

EXTRACTION_PROMPT = """You are an expert meeting analyst working for an enterprise organisation.

Your job is to carefully read a meeting transcript and extract structured information.

Extract the following:
1. ALL action items - things people committed to doing
2. ALL decisions made - things the team agreed on
3. A clear summary of the meeting in 2-3 sentences
4. The next meeting date and time if mentioned

RULES:
- Only extract what is explicitly stated or clearly implied
- For action items: identify who said they would do something
- For priority: High if urgent/blocking, Medium if important, Low if nice to have
- If something is unclear, still extract it but note the uncertainty in the task description
- Return ONLY valid JSON - no explanation, no markdown, no extra text

Return this exact JSON structure:
{{
    "action_items": [
        {{
            "task": "description of what needs to be done",
            "owner": "person responsible or null if unclear",
            "deadline": "when by or null if not mentioned",
            "priority": "High or Medium or Low"
        }}
    ],
    "decisions": [
        {{
            "decision": "what was decided",
            "context": "why or how it came up or null"
        }}
    ],
    "summary": "2-3 sentence overview of the meeting",
    "next_meeting": "date and time or null if not mentioned"
}}

MEETING TRANSCRIPT:
{transcript}

Return ONLY the JSON object. Nothing else."""


def extract_from_transcript(transcript: str) -> MeetingSummary:
    """
    Takes a raw meeting transcript and returns structured data.
    
    Args:
        transcript: the full meeting transcript as a string
        
    Returns:
        MeetingSummary object with action items, decisions, summary
        
    Raises:
        ValueError: if the AI returns invalid JSON or missing fields
    """
    try:
        # Step 1 — Format the prompt
        formatted_prompt = EXTRACTION_PROMPT.format(transcript=transcript)
        
        # Step 2 — Send to Ollama and get response
        response = llm.invoke(formatted_prompt)
        raw_text = response.content.strip()
        
        # Step 3 — Clean and parse the JSON
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = [line for line in lines if not line.startswith("```")]
            raw_text = "\n".join(lines)
        
        raw_text = raw_text.strip()
        data = json.loads(raw_text)
        
        # Step 4 — Validate through Pydantic and return
        summary = MeetingSummary(**data)
        return summary
        
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {str(e)}\nRaw response: {raw_text}")
    
    except Exception as e:
        raise ValueError(f"Extraction failed: {str(e)}")
    

if __name__ == "__main__":
    
    # A realistic test transcript
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
    
    print("Sending transcript to Ollama...")
    print("This takes 10-30 seconds - AI is thinking locally on your Mac")
    print("-" * 50)
    
    result = extract_from_transcript(test_transcript)
    
    print(f"SUMMARY: {result.summary}")
    print()
    print(f"ACTION ITEMS ({len(result.action_items)} found):")
    for item in result.action_items:
        print(f"  - {item.task}")
        print(f"    Owner: {item.owner}")
        print(f"    Deadline: {item.deadline}")
        print(f"    Priority: {item.priority}")
    print()
    print(f"DECISIONS ({len(result.decisions)} found):")
    for decision in result.decisions:
        print(f"  - {decision.decision}")
    print()
    print(f"NEXT MEETING: {result.next_meeting}")
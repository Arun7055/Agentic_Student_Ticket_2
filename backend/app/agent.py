import os
from typing import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq
from typing import List, Optional

# 1. THE MASTER CLIPBOARD DICTIONARY
DEPARTMENT_REQUIREMENTS = {
    "hostel": ["room_number", "specific_appliance_or_issue", "is_active_leak_or_spark"],
    "fee": ["student_id_number", "transaction_reference_number", "date_of_payment", "amount_charged"],
    "exam": ["course_code", "exam_date", "hall_ticket_number"],
    "library": ["book_title_or_barcode", "date_borrowed"],
    "placements": ["company_name", "interview_date", "specific_document_needed"],
    "academics": ["professor_name", "subject_name", "nature_of_request"],
    "admin": ["vehicle_number_or_id_type", "exact_location_on_campus"]
}

# 2. THE NEW DYNAMIC SLOT-FILLING CONTRACT
class TriageDecision(BaseModel):
    agent_reply: str = Field(
        description="The natural language response to send back to the student."
    )
    is_clipboard_complete: bool = Field(
        description="MUST be a strict boolean (true or false), do not use strings."
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="MUST be a valid JSON array of strings. If no information is missing, return an empty array []."
    )
    department_slug: Optional[str] = Field(
        default=None, 
        description="The assigned department queue (e.g., hostel, admin, exam, placements, it)."
    )
    severity: Optional[str] = Field(
        default=None, 
        description="LOW, MEDIUM, or HIGH"
    )
    issue_summary: Optional[str] = Field(
        default=None, 
        description="A brief summary of the issue."
    )

# 3. GRAPH STATE
class TicketState(TypedDict):
    messages: Annotated[list, add_messages]
    department: str | None
    severity: str | None
    is_clipboard_complete: bool
    missing_information: list[str]
    issue_summary: str | None

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,  
    api_key=os.getenv("GROQ_API_KEY")
)

structured_router = llm.with_structured_output(TriageDecision)

def get_system_prompt():
    req_str = "\n".join([f"- {dept}: requires {', '.join(fields)}" for dept, fields in DEPARTMENT_REQUIREMENTS.items()])
    return f"""You are the AI Front Desk Triage officer for a college IT desk.
Your job is to identify the student's department and strictly verify if they have provided all necessary diagnostic information.

DEPARTMENT CHECKLISTS:
{req_str}

RULES:
1. Identify the department based on the student's problem.
2. Cross-reference the chat history against that department's required fields.
3. If ANY field is missing, set is_clipboard_complete to False and ask for the missing details.
4. Only set is_clipboard_complete to True when ALL fields for that department are explicitly answered in the chat log.
"""

async def triage_node(state: TicketState):
    conversation_history = state["messages"]
    messages_to_pass = [SystemMessage(content=get_system_prompt())] + conversation_history
    
    decision: TriageDecision = await structured_router.ainvoke(messages_to_pass)
    reply_msg = AIMessage(content=decision.agent_reply)
    
    return {
        "messages": [reply_msg],
        "department": decision.department_slug,
        "severity": decision.severity,
        "is_clipboard_complete": decision.is_clipboard_complete,
        "missing_information": decision.missing_information,
        "issue_summary": decision.issue_summary
    }

# 4. BUILD THE GRAPH ENGINE
graph_builder = StateGraph(TicketState)
graph_builder.add_node("triage", triage_node)
graph_builder.add_edge(START, "triage")
graph_builder.add_edge("triage", END)
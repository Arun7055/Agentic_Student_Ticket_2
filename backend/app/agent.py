import os
from typing import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq

# 1. THE CONTRACT: Groq is strictly forced to return this exact JSON shape
class TicketDecision(BaseModel):
    department: Literal["hostel", "admin", "exam", "placements", "library", "academics", "fee"] = Field(
        description="The specific college department responsible for solving this issue."
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="HIGH: Immediate safety hazard, water/power outage, exam tomorrow, financial portal blocked today. MEDIUM: Standard broken item, routine document needed this week. LOW: General casual inquiry."
    )
    student_reply: str = Field(
        description="A warm, reassuring, professional 1-2 sentence reply to the student acknowledging their issue."
    )

# 2. GRAPH STATE
class TicketState(TypedDict):
    messages: Annotated[list, add_messages]
    department: str | None
    severity: str | None

# 3. THE ENGINE
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,  # Near-zero temp so it acts like deterministic software, not a poet
    api_key=os.getenv("GROQ_API_KEY")
)

# Bind the Pydantic contract to the Groq model
structured_router = llm.with_structured_output(TicketDecision)

SYSTEM_PROMPT = """You are the AI Front Desk Triage officer for a college. 
Analyze the student's message and categorize it into one of the 7 departments:
- hostel: dorm rooms, roommates, mess food, room wifi, plumbing, furniture, electricity
- admin: ID cards, bonafide certificates, campus security, general college parking/rules
- exam: hall tickets, seating arrangements, re-evaluation, grade sheets, exam timetable
- placements: internships, resume verification, company drives, interview NOC letters
- library: lost books, fine waivers, portal access, e-journal subscriptions
- academics: class timetable, syllabus, subject registration, attendance % issues, faculty issues
- fee: tuition payment receipts, scholarship portal, fee breakdown, payment gateway failures
"""

async def triage_node(state: TicketState):
    conversation_history = state["messages"]
    
    # Pack the system prompt at the very front of the chat log
    messages_to_pass = [SystemMessage(content=SYSTEM_PROMPT)] + conversation_history
    
    # Groq thinks for 0.4 seconds and returns a populated TicketDecision object
    decision: TicketDecision = await structured_router.ainvoke(messages_to_pass)
    
    # Turn the AI's drafted string into a formal LangGraph AIMessage
    reply_msg = AIMessage(content=decision.student_reply)
    
    return {
        "messages": [reply_msg],
        "department": decision.department,
        "severity": decision.severity
    }

# Build the graph
graph_builder = StateGraph(TicketState)
graph_builder.add_node("triage", triage_node)
graph_builder.add_edge(START, "triage")
graph_builder.add_edge("triage", END)
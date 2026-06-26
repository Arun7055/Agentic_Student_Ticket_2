from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from uuid import UUID, uuid4
import os

from app.database import init_db, get_session
from app.models import User, Ticket, TicketMessage
from app.agent import graph_builder
from app.services import assign_ticket_to_faculty
from sqlmodel import select

compiled_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_graph
    print("🚀 Booting up: Syncing SQLModel tables...")
    await init_db()
    
    print("🧠 Booting up: Hooking LangGraph subconscious into Neon DB...")
    raw_db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    
    if "?ssl=require" in raw_db_url:
        raw_db_url = raw_db_url.replace("?ssl=require", "?sslmode=require")
    elif "&ssl=require" in raw_db_url:
        raw_db_url = raw_db_url.replace("&ssl=require", "&sslmode=require")

    async with AsyncConnectionPool(conninfo=raw_db_url, max_size=10, kwargs={"autocommit": True}) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup() 
        
        compiled_graph = graph_builder.compile(checkpointer=checkpointer)
        print("🟢 Brain & Spine fully synchronized.")
        yield

    print("💤 Shutting down...")

# ---> THIS WAS THE MISSING LINE <---
app = FastAPI(title="Ticketing Gateway v2", lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "Spine is online"}

@app.post("/test-db")
async def create_test_user(session: AsyncSession = Depends(get_session)):
    dummy = User(email=f"arun_{uuid4().hex[:4]}@college.edu", full_name="Arun Test")
    session.add(dummy)
    await session.commit()
    await session.refresh(dummy)
    return {"message": "Success! Written to Neon.", "user": dummy}

class ChatInitRequest(BaseModel):
    student_id: UUID
    thread_id: str
    message: str

class HumanMessageRequest(BaseModel):
    ticket_id: UUID
    sender_id: UUID
    sender_type: str # 'STUDENT' or 'FACULTY'
    content: str

@app.post("/chat/ai")
async def ai_triage_chat(payload: ChatInitRequest, db: AsyncSession = Depends(get_session)):
    if not compiled_graph:
        raise HTTPException(status_code=500, detail="Graph engine offline")

    # 1. Ensure Ticket Row Exists
    stmt = select(Ticket).where(Ticket.thread_id == payload.thread_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    
    if not ticket:
        ticket = Ticket(thread_id=payload.thread_id, student_id=payload.student_id)
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

    if ticket.status != "AI_TRIAGE":
        raise HTTPException(status_code=400, detail="Ticket is already assigned to a human agent.")

    # 2. Save Student Message
    user_msg = TicketMessage(ticket_id=ticket.id, sender_type="STUDENT", sender_id=payload.student_id, content=payload.message)
    db.add(user_msg)
    await db.commit()

    # 3. Invoke Groq Brain
    config = {"configurable": {"thread_id": payload.thread_id}}
    result = await compiled_graph.ainvoke({"messages": [HumanMessage(content=payload.message)]}, config=config)
    ai_reply_text = result["messages"][-1].content
    dept = result.get("department")
    sev = result.get("severity")

    # 4. Save AI Response Message
    ai_msg = TicketMessage(ticket_id=ticket.id, sender_type="AI", content=ai_reply_text)
    db.add(ai_msg)
    await db.commit()

    # 5. Check if ready for Dispatch (Human Takeover)
    if dept and dept != "unclassified":
        ticket = await assign_ticket_to_faculty(db, payload.thread_id, dept, sev)

    return {
        "ticket_id": ticket.id,
        "status": ticket.status,
        "assigned_dept": ticket.department,
        "assigned_faculty": ticket.assigned_faculty_id,
        "reply": ai_reply_text
    }

@app.post("/chat/human")
async def human_direct_chat(payload: HumanMessageRequest, db: AsyncSession = Depends(get_session)):
    msg = TicketMessage(
        ticket_id=payload.ticket_id,
        sender_id=payload.sender_id,
        sender_type=payload.sender_type,
        content=payload.content
    )
    db.add(msg)
    await db.commit()
    return {"status": "delivered", "timestamp": msg.created_at}
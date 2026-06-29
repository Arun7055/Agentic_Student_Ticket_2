from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage
from sqlmodel import select

from app.database import get_session
from app.models import Ticket, TicketMessage
from app.schemas import ChatInitRequest, HumanMessageRequest
from app.services import assign_ticket_to_faculty
import app.main as master  # Lazy reference to access the globally compiled graph

router = APIRouter(prefix="/chat", tags=["Chat & Triage"])

@router.post("/ai")
async def ai_triage_chat(payload: ChatInitRequest, db: AsyncSession = Depends(get_session)):
    if not master.compiled_graph:
        raise HTTPException(status_code=500, detail="Graph engine offline")

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

    user_msg = TicketMessage(ticket_id=ticket.id, sender_type="STUDENT", sender_id=payload.student_id, content=payload.message)
    db.add(user_msg)
    await db.commit()

    config = {"configurable": {"thread_id": payload.thread_id}}
    result = await master.compiled_graph.ainvoke({"messages": [HumanMessage(content=payload.message)]}, config=config)
    ai_reply_text = result["messages"][-1].content
    dept = result.get("department")
    sev = result.get("severity")

    ai_msg = TicketMessage(ticket_id=ticket.id, sender_type="AI", content=ai_reply_text)
    db.add(ai_msg)
    await db.commit()

    if dept and dept != "unclassified":
        ticket = await assign_ticket_to_faculty(db, payload.thread_id, dept, sev)

    return {
        "ticket_id": ticket.id,
        "status": ticket.status,
        "assigned_dept": ticket.department,
        "assigned_faculty": ticket.assigned_faculty_id,
        "reply": ai_reply_text
    }

@router.post("/human")
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
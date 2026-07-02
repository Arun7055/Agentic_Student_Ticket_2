from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.dependencies import get_current_user
from app.models import Ticket, User, TicketMessage
from app.schemas import TicketResolveRequest
from app.agent import llm

# The prefix "/tickets" applies to every route in this file automatically!
router = APIRouter(prefix="/tickets", tags=["Tickets & Dashboards"])

@router.get("/")
async def get_my_tickets(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Smart Dashboard Endpoint (Student vs Faculty)."""
    if current_user.role == "FACULTY":
        stmt = select(Ticket).where(
            Ticket.department == current_user.department_slug
        ).order_by(Ticket.created_at.desc())
    else:
        stmt = select(Ticket).where(
            Ticket.student_id == current_user.id
        ).order_by(Ticket.created_at.desc())
        
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{ticket_id}/copilot")
async def faculty_ai_copilot(
    ticket_id: UUID, 
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Faculty tool: Analyzes transcript and summarizes the issue."""
    if current_user.role != "FACULTY":
        raise HTTPException(status_code=403, detail="Only faculty can access the Copilot.")

    stmt = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at)
    res = await db.execute(stmt)
    messages = res.scalars().all()

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this ticket.")

    chat_transcript = "\n".join([f"[{m.sender_type}]: {m.content}" for m in messages])
    copilot_prompt = f"""You are an AI Copilot assisting a college professor. 
Read the following support ticket transcript and provide a 2-bullet-point summary:
1. The Core Issue (what is physically broken/needed)
2. The Student's emotional state

TRANSCRIPT:
{chat_transcript}
"""
    response = await llm.ainvoke(copilot_prompt)
    return {"ticket_id": ticket_id, "message_count": len(messages), "copilot_analysis": response.content}


@router.patch("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: UUID, 
    payload: TicketResolveRequest, 
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Securely closes a ticket and logs the resolution note."""
    if current_user.role != "FACULTY":
        raise HTTPException(status_code=403, detail="Only faculty can resolve tickets.")

    stmt = select(Ticket).where(Ticket.id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    if ticket.department != current_user.department_slug:
        raise HTTPException(status_code=403, detail="You can only resolve tickets in your assigned department.")

    # Using "CLOSED" to match the frontend UI we built earlier!
    if ticket.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Ticket is already marked as closed.")

    ticket.status = "CLOSED"
    db.add(ticket)

    if payload.resolution_note:
        closing_receipt = TicketMessage(
            ticket_id=ticket.id,
            sender_type="FACULTY",
            sender_id=current_user.id,
            content=f"✔ [SYSTEM]: Ticket officially closed. Resolution Note: {payload.resolution_note}"
        )
        db.add(closing_receipt)

    await db.commit()
    await db.refresh(ticket)

    return {
        "ticket_id": ticket.id,
        "new_status": ticket.status,
        "freed_faculty_id": ticket.assigned_faculty_id,
        "message": "Ticket successfully resolved."
    }
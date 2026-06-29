from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select
from uuid import UUID

from app.database import get_session
from app.models import User, Ticket, TicketMessage
from app.schemas import FacultyCreateRequest, TicketResolveRequest
from app.agent import llm

router = APIRouter(tags=["Faculty & Admin"])

@router.post("/admin/faculty", status_code=201)
async def onboard_faculty(payload: FacultyCreateRequest, db: AsyncSession = Depends(get_session)):
    valid_depts = ["hostel", "admin", "exam", "placements", "library", "academics", "fee"]
    if payload.department_slug not in valid_depts:
        raise HTTPException(status_code=400, detail=f"Invalid department. Must be one of: {valid_depts}")

    new_faculty = User(
        email=payload.email,
        full_name=payload.full_name,
        role="FACULTY",
        department_slug=payload.department_slug
    )
    db.add(new_faculty)
    await db.commit()
    await db.refresh(new_faculty)
    return {"message": "Faculty onboarded successfully", "faculty": new_faculty}

@router.get("/admin/roster/{department_slug}")
async def get_department_roster(department_slug: str, db: AsyncSession = Depends(get_session)):
    stmt = (
        select(User, func.count(Ticket.id).label("active_tickets"))
        .outerjoin(Ticket, (Ticket.assigned_faculty_id == User.id) & (Ticket.status.in_(["OPEN", "IN_PROGRESS"])))
        .where(User.role == "FACULTY", User.department_slug == department_slug)
        .group_by(User.id)
    )
    res = await db.execute(stmt)
    roster = [{"faculty_id": row[0].id, "name": row[0].full_name, "active_tickets": row[1]} for row in res.all()]
    return {"department": department_slug, "staff_count": len(roster), "roster": roster}

@router.get("/faculty/copilot/{ticket_id}")
async def faculty_ai_copilot(ticket_id: UUID, db: AsyncSession = Depends(get_session)):
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


@router.patch("/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: UUID, payload: TicketResolveRequest, db: AsyncSession = Depends(get_session)):
    # 1. Fetch the target ticket
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found in database.")

    if ticket.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Ticket is already marked as resolved.")

    # 2. Mutate the state
    ticket.status = "RESOLVED"
    db.add(ticket)

    # 3. If the teacher left a parting note, bake it into the immutable chat log
    if payload.resolution_note:
        closing_receipt = TicketMessage(
            ticket_id=ticket.id,
            sender_type="FACULTY",
            sender_id=ticket.assigned_faculty_id,
            content=f"✔ [SYSTEM]: Ticket officially closed. Resolution Note: {payload.resolution_note}"
        )
        db.add(closing_receipt)

    await db.commit()
    await db.refresh(ticket)

    return {
        "ticket_id": ticket.id,
        "new_status": ticket.status,
        "freed_faculty_id": ticket.assigned_faculty_id,
        "message": "Ticket successfully reaped from active rotation."
    }
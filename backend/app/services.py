from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Ticket, User

async def assign_ticket_to_faculty(db: AsyncSession, thread_id: str, department: str, severity: str):
    # 1. Fetch the ticket
    stmt = select(Ticket).where(Ticket.thread_id == thread_id)
    result = await db.execute(stmt)
    ticket = result.scalars().first()
    
    if not ticket:
        return None

    # 2. Find a faculty member in that department
    fac_stmt = select(User).where(User.role == "FACULTY", User.department_slug == department)
    fac_result = await db.execute(fac_stmt)
    faculty = fac_result.scalars().first()

    # 3. Update the ticket status
    ticket.department = department
    ticket.severity = severity
    ticket.status = "OPEN"
    
    if faculty:
        ticket.assigned_faculty_id = faculty.id

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket
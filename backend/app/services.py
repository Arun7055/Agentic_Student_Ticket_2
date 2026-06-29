from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Ticket, User

async def assign_ticket_to_faculty(db: AsyncSession, thread_id: str, department: str, severity: str):
    # 1. Fetch the ticket
    stmt = select(Ticket).where(Ticket.thread_id == thread_id)
    result = await db.execute(stmt)
    ticket = result.scalars().first()
    
    if not ticket:
        return None

    # 2. THE LOAD BALANCER QUERY:
    # Find all faculty in this department, left join their open tickets, and count them.
    # Order by workload ASC so the least-busy teacher is always row [0].
    workload_stmt = (
        select(User, func.count(Ticket.id).label("active_tickets"))
        .outerjoin(Ticket, (Ticket.assigned_faculty_id == User.id) & (Ticket.status.in_(["OPEN", "IN_PROGRESS"])))
        .where(User.role == "FACULTY", User.department_slug == department)
        .group_by(User.id)
        .order_by("active_tickets")
    )
    
    fac_result = await db.execute(workload_stmt)
    least_busy_row = fac_result.first() # Returns a tuple: (User_Object, ticket_count)

    # 3. Update the ticket
    ticket.department = department
    ticket.severity = severity
    ticket.status = "OPEN"
    
    if least_busy_row:
        assigned_faculty = least_busy_row[0]
        ticket.assigned_faculty_id = assigned_faculty.id

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select

from app.database import get_session
from app.models import User, Ticket
from app.schemas import FacultyCreateRequest

router = APIRouter(tags=["Admin Operations"])

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
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from app.database import get_session
from app.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

FACULTY_SECRET_KEY = "super_secret_faculty_key_for_dev" 

class LoginRequest(BaseModel):
    staff_id: str  # Changed from email
    password: str

@router.post("/faculty/login")
async def faculty_login(payload: LoginRequest, db: AsyncSession = Depends(get_session)):
    """Validates faculty credentials using their Department Slug as their Staff ID."""
    
    # Search by department_slug instead of email
    stmt = select(User).where(
        User.department_slug == payload.staff_id.lower(), 
        User.role == "FACULTY"
    )
    user = (await db.execute(stmt)).scalars().first()

    if not user or user.password != payload.password:
        raise HTTPException(status_code=401, detail="Invalid Staff ID or password")

    # Issue a custom JWT token containing the user ID
    token = jwt.encode(
        {
            "sub": str(user.id), 
            "role": "FACULTY", 
            "exp": datetime.utcnow() + timedelta(days=7)
        },
        FACULTY_SECRET_KEY, 
        algorithm="HS256"
    )
    
    return {"access_token": token, "token_type": "bearer"}
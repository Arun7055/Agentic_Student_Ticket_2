from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/users", tags=["Identity"])

@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    The Identity Endpoint: 
    Returns the currently authenticated user's Postgres database row.
    The Next.js frontend uses this to determine if they are STUDENT or FACULTY.
    """
    return current_user
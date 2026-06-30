from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class ChatInitRequest(BaseModel):
    thread_id: str
    message: str

class HumanMessageRequest(BaseModel):
    ticket_id: UUID
    sender_id: UUID
    sender_type: str  # 'STUDENT' or 'FACULTY'
    content: str

class FacultyCreateRequest(BaseModel):
    email: str
    full_name: str
    department_slug: str 

# ---> NEW REAPER CONTRACT <---
class TicketResolveRequest(BaseModel):
    resolution_note: Optional[str] = None
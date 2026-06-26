from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP  # <-- Notice TIMESTAMP added here

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    role: str = Field(default="STUDENT") 
    department_slug: Optional[str] = Field(default=None, index=True) 

class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    thread_id: str = Field(unique=True, index=True)
    student_id: UUID = Field(foreign_key="users.id")
    assigned_faculty_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    department: Optional[str] = Field(default=None, index=True)
    severity: Optional[str] = None
    status: str = Field(default="AI_TRIAGE", index=True) 
    structured_payload: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    
    # EXPLICIT TIMEZONE AWARE COLUMN:
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )

class TicketMessage(SQLModel, table=True):
    __tablename__ = "ticket_messages"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="tickets.id", index=True)
    sender_type: str 
    sender_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    content: str
    
    # EXPLICIT TIMEZONE AWARE COLUMN:
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
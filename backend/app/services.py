import os
import asyncio
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from uuid import UUID
from sqlalchemy import func
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine  
from app.models import Ticket, User, TicketMessage

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
    
# Grab credentials from environment
GMAIL_USER = os.getenv("GMAIL_USER") # Your full @gmail.com address
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD") # The 16-character App Password

def _send_sync_email(to_email: str, subject: str, html_body: str):
    """Synchronous helper that physically talks to Google SMTP over Port 465 (SSL)."""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("❌ Gmail credentials missing in .env")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Campus IT Desk <{GMAIL_USER}>"
    msg["To"] = to_email

    part = MIMEText(html_body, "html")
    msg.attach(part)

    try:
        # Port 465 is Google's secure SSL SMTP tunnel
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
            print(f"📧 Native Email successfully shot to: {to_email}")
    except Exception as e:
        print(f"❌ SMTP Handshake Failed: {e}")

async def dispatch_ticket_emails(ticket_id: UUID):
    """Decoupled background daemon with explicit crash logging."""
    print(f"🔄 Background Mailer triggered for Ticket: {ticket_id}")
    try:
        async with AsyncSession(engine) as db:
            ticket = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalars().first()
            if not ticket or not ticket.assigned_faculty_id:
                print("❌ Mail Aborted: Ticket or assigned faculty missing in DB.")
                return

            student = (await db.execute(select(User).where(User.id == ticket.student_id))).scalars().first()
            faculty = (await db.execute(select(User).where(User.id == ticket.assigned_faculty_id))).scalars().first()

            if not student or not faculty:
                print("❌ Mail Aborted: Student or Faculty user rows missing in DB.")
                return

            stmt_msg = select(TicketMessage).where(
                TicketMessage.ticket_id == ticket_id, 
                TicketMessage.sender_type == "STUDENT"
            ).order_by(TicketMessage.created_at.asc())
            
            first_msg = (await db.execute(stmt_msg)).scalars().first()
            raw_prompt = first_msg.content if first_msg else "No transcript recorded."

            vault = ticket.structured_payload or {}
            summary = vault.get("issue_summary", "New Campus Issue")
            sev = vault.get("severity", "MEDIUM")

            # 1. Prepare Faculty Dossier HTML
            faculty_html = f"""
            <div style="font-family: sans-serif; max-width: 600px; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #d9534f; margin-top:0;">🚨 New IT Dossier Routed</h2>
                <p><strong>Assigned Queue:</strong> {ticket.department.upper()}</p>
                <p><strong>Student Contact:</strong> {student.full_name} (<a href="mailto:{student.email}">{student.email}</a>)</p>
                <hr style="border: 0; border-top: 1px solid #eee;"/>
                <p><strong>AI Executive Summary:</strong><br/> {summary}</p>
                <p><strong>Original Student Message:</strong><br/> <em>"{raw_prompt}"</em></p>
            </div>
            """

            # 2. Prepare Student Receipt HTML
            student_html = f"""
            <div style="font-family: sans-serif; max-width: 600px; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #5cb85c; margin-top:0;">✔ Ticket Triaged & Assigned</h2>
                <p>Your issue has been categorized by the AI Front Desk and routed to staff.</p>
                <p><strong>Assigned Officer:</strong> {faculty.full_name}</p>
                <p><strong>Logged Summary:</strong> {summary}</p>
                <p><strong>Ticket Reference:</strong> #{ticket.id}</p>
            </div>
            """

            print(f"📤 Handing off SMTP tasks for {faculty.email} and {student.email}...")
            await asyncio.to_thread(_send_sync_email, faculty.email, f"[{sev}] Action Required: {summary}", faculty_html)
            await asyncio.to_thread(_send_sync_email, student.email, f"Receipt: Ticket #{str(ticket.id)[:8]} Assigned", student_html)
            
    except Exception as e:
        print("\n" + "="*50)
        print("🚨 CRITICAL CRASH IN BACKGROUND MAILER DAEMON:")
        traceback.print_exc()
        print("="*50 + "\n")
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

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

def _send_sync_email(to_email: str, subject: str, html_body: str):
    """Bypasses SMTP by using Brevo's HTTP API with a verified Gmail sender."""
    if not BREVO_API_KEY:
        print("❌ Brevo API key missing in .env", flush=True)
        return

    # 1. Brevo's specific JSON payload structure
    payload = {
        "sender": {
            "name": "Campus IT Desk",
            "email": "saiarunkumar1615@gmail.com" # 👈 Must match your verified Brevo account email
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": subject,
        "htmlContent": html_body
    }
    
    data = json.dumps(payload).encode("utf-8")
    
    # 2. Package it for the Brevo endpoint
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    # 3. Fire the request
    try:
        print(f"🌐 Thread started: Attempting to contact Brevo for {to_email}...", flush=True)
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status in [200, 201, 202]:
                print(f"✅ Brevo API Email successfully shot to: {to_email}", flush=True)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Brevo Email Failed with code {e.code}: {error_body}", flush=True)
    except Exception as e:
        print(f"❌ Brevo Email completely crashed: {e}", flush=True)

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
                <p><strong>Assigned Officer:</strong> {faculty.full_name}(<a href="mailto:{faculty.email}">{faculty.email}</a>)</p>
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
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage
from sqlmodel import select

from app.database import get_session
from app.dependencies import get_current_user
from app.models import Ticket, TicketMessage, User
from app.schemas import ChatInitRequest, HumanMessageRequest
from app.services import assign_ticket_to_faculty, dispatch_ticket_emails
import app.main as master

router = APIRouter(tags=["Chat & Triage"])

@router.post("/ai")
async def ai_triage_chat(
    payload: ChatInitRequest, 
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user) # Secure Bouncer added to legacy route
):
    """Legacy blocking endpoint for Swagger UI testing."""
    if not master.compiled_graph:
        raise HTTPException(status_code=500, detail="Graph engine offline")

   # Fetch or create ticket row using the ID directly!
    stmt = select(Ticket).where(Ticket.id == payload.thread_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    
    if not ticket:
        # Force the database to use the frontend's UUID as the official primary key
        ticket = Ticket(
            id=payload.thread_id, 
            thread_id=payload.thread_id, 
            student_id=current_user.id,
            status="AI_TRIAGE"
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

    if ticket.status != "AI_TRIAGE":
        raise HTTPException(status_code=400, detail="Ticket is already assigned to human staff.")

    user_msg = TicketMessage(
        ticket_id=ticket.id, 
        sender_type="STUDENT", 
        sender_id=current_user.id, 
        content=payload.message
    )
    db.add(user_msg)
    await db.commit()

    config = {"configurable": {"thread_id": payload.thread_id}}
    result = await master.compiled_graph.ainvoke({"messages": [HumanMessage(content=payload.message)]}, config=config)
    ai_reply_text = result["messages"][-1].content
    dept = result.get("department")
    sev = result.get("severity")
    summary = result.get("issue_summary")

    ai_msg = TicketMessage(ticket_id=ticket.id, sender_type="AI", content=ai_reply_text)
    db.add(ai_msg)

    ticket.structured_payload = {
        "department": dept,
        "severity": sev,
        "issue_summary": summary,
        "raw_student_prompt": payload.message
    }
    db.add(ticket)
    await db.commit()

    if dept and dept != "unclassified":
        await assign_ticket_to_faculty(db, payload.thread_id, dept, sev)

    return {
        "ticket_id": ticket.id,
        "status": ticket.status,
        "assigned_dept": ticket.department,
        "assigned_faculty": ticket.assigned_faculty_id,
        "reply": ai_reply_text
    }

@router.post("/ai/stream")
async def stream_ai_triage_chat(
    payload: ChatInitRequest, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Production SSE streaming endpoint for Next.js frontend."""
    if not master.compiled_graph:
        raise HTTPException(status_code=500, detail="Graph engine offline")

    # ---> ANTI-CONCURRENCY SHIELD <---
    active_stmt = select(Ticket).where(
        Ticket.student_id == current_user.id, 
        Ticket.status == "AI_TRIAGE"
    )
    active_ticket = (await db.execute(active_stmt)).scalars().first()
    
    # if active_ticket and active_ticket.thread_id != payload.thread_id:
    #     raise HTTPException(
    #         status_code=409, 
    #         detail="Concurrency Lock: You already have an active diagnostic session open in another tab."
    #     )

    try:
        real_uuid = uuid.UUID(payload.thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format from frontend")

    # 2. Query using the real_uuid object
    stmt = select(Ticket).where(Ticket.id == real_uuid)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    
    # 3. Create using the real_uuid object if it doesn't exist
    if not ticket:
        ticket = Ticket(
            id=real_uuid, 
            thread_id=payload.thread_id,
            student_id=current_user.id,
            status="AI_TRIAGE"
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

    if ticket.status != "AI_TRIAGE":
        raise HTTPException(status_code=400, detail="Ticket is already assigned to human staff.")

    # Log Student Message
    user_msg = TicketMessage(
        ticket_id=ticket.id, 
        sender_type="STUDENT", 
        sender_id=current_user.id,
        content=payload.message
    )
    db.add(user_msg)
    await db.commit()

    # The duplicated block that was causing the crash has been permanently deleted from here!

    async def event_generator():
        config = {"configurable": {"thread_id": payload.thread_id}}
        final_state = None

        async for event in master.compiled_graph.astream_events(
            {"messages": [HumanMessage(content=payload.message)]}, 
            config=config, 
            version="v2"
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # Tweaked to "content" to perfectly match the Next.js parser!
                    packet = json.dumps({"content": content, "is_done": False})
                    yield f"data: {packet}\n\n"
                    
            elif kind == "on_chain_end" and event["name"] == "triage":
                final_state = event["data"]["output"]

        if final_state:
            ai_reply_text = final_state["messages"][-1].content
            is_complete = final_state.get("is_clipboard_complete", False)
            dept = final_state.get("department")
            sev = final_state.get("severity")
            summary = final_state.get("issue_summary")

            ai_msg = TicketMessage(ticket_id=ticket.id, sender_type="AI", content=ai_reply_text)
            db.add(ai_msg)

            ticket.structured_payload = {
                "department": dept,
                "severity": sev,
                "issue_summary": summary,
                "missing_information": final_state.get("missing_information", []),
                "is_clipboard_complete": is_complete
            }
            db.add(ticket)
            await db.commit()

            # ---> THE GATEKEEPER & BACKGROUND MAILER <---
            if is_complete and dept and dept != "unclassified":
                await assign_ticket_to_faculty(db, payload.thread_id, dept, sev)
                print(f"⚡ Gatekeeper opened. Queuing email dispatch for ticket: {ticket.id}")
                background_tasks.add_task(dispatch_ticket_emails, ticket.id)

        yield f"data: {json.dumps({'is_done': True, 'clipboard_complete': is_complete})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/human")
async def human_direct_chat(payload: HumanMessageRequest, db: AsyncSession = Depends(get_session)):
    """Direct human-to-human messaging once AI triage is closed."""
    msg = TicketMessage(
        ticket_id=payload.ticket_id,
        sender_id=payload.sender_id,
        sender_type=payload.sender_type,
        content=payload.content
    )
    db.add(msg)
    await db.commit()
    return {"status": "delivered", "timestamp": msg.created_at}
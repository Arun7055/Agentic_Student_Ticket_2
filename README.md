# 🤖 Agentic Student Ticket System

An intelligent, AI-driven IT Support diagnostic system for university students. This full-stack application uses an autonomous LangGraph agent to triage student issues in real-time via a streaming chat interface, automatically routing complete tickets to the appropriate faculty department.

### 🔴 Live Demo
**[Launch the Application](https://agentic-student-ticket-2.vercel.app)** *(Note: Requires authentication. Use the Clerk login to access the student portal).*

---

## 🏗️ Architecture & Tech Stack

This project is structured as a monorepo containing a decoupled Next.js frontend and an asynchronous FastAPI Python backend.

<img width="516" height="532" alt="image" src="https://github.com/user-attachments/assets/261b667c-5f78-4517-aacf-01c2a77990bc" />
<img width="459" height="551" alt="image" src="https://github.com/user-attachments/assets/10dbe51a-4284-4e00-92eb-baa64f86453c" />



**Frontend (Deployed on Vercel):**
* **Framework:** Next.js 14 (App Router)
* **Styling:** Tailwind CSS & Lucide Icons
* **Authentication:** Clerk (Edge-compatible Middleware)
* **Data Fetching:** Native `fetch` with Server-Sent Events (SSE) parsing

**Backend (Deployed on Render):**
* **Framework:** FastAPI (Python 3.12) & Uvicorn
* **AI Agent:** LangGraph & LangChain (using Groq for high-speed inference)
* **Database ORM:** SQLModel & SQLAlchemy (Asyncpg)
* **Database Hosting:** Neon DB (Serverless PostgreSQL)

---

## 🔄 How the Workflow Operates

This application is designed to mimic a human IT diagnostic session while guaranteeing data integrity and concurrency control. Here is the step-by-step lifecycle of a ticket:

1. **Secure Handshake:** A student logs into the Next.js portal via Clerk. The frontend retrieves a secure JWT token.
   <img width="423" height="509" alt="Screenshot 2026-07-07 at 11 09 42 PM" src="https://github.com/user-attachments/assets/45425c0b-778b-4053-aab7-bf9df6129699" />
  <img width="1283" height="832" alt="Screenshot 2026-07-07 at 11 09 15 PM" src="https://github.com/user-attachments/assets/9e4f9707-394c-48a6-9d31-00189dab863f" />


2. **Ticket Initialization:** When the student clicks "New Ticket," the frontend generates a cryptographically secure `UUID` and routes the user to a dynamic chat room (`/portal/tickets/[ticketId]`).
<img width="1294" height="835" alt="Screenshot 2026-07-07 at 11 04 51 PM" src="https://github.com/user-attachments/assets/9ffebbda-1fbf-4862-a618-115c425474e1" />
  
3. **Database Synchronization:** The frontend sends the first message to the backend via a `POST` request. The FastAPI backend verifies the Clerk JWT, validates the `UUID`, and creates a new `Ticket` row in the Neon Postgres database with the status `AI_TRIAGE`.
<img width="1328" height="834" alt="Screenshot 2026-07-07 at 11 05 27 PM" src="https://github.com/user-attachments/assets/917eb70d-eee2-4d94-8055-a339274e9725" />

4. **Agentic Streaming (SSE):** The message is passed into the compiled LangGraph agent. As the LLM reasons about the IT issue, FastAPI streams the text chunks back to the Next.js frontend using Server-Sent Events (SSE) for a real-time typing effect.
5. **Information Gathering:** If the AI determines it lacks required data (e.g., a specific error code, a Wi-Fi location, or a transaction ID), it asks follow-up questions. The conversation history is persisted in the database to maintain state.
6. **Final Payload & Routing:** Once the AI has all necessary parameters, it outputs a structured JSON payload containing the `department`, `severity`, and `issue_summary`. 
6. **UI Lock & Dispatch:** The database status is updated, triggering the frontend UI to instantly lock the chat input, display a "Routed to Faculty" badge, and queue a background task to notify the relevant department.
7. Once routed to faculty, the agent sends a mail summarizing the issue to the student as well as assigned faculty. Their mails are shared with each other. The faculty discusses the issue with the student and can close the ticket.
<img width="481" height="475" alt="Screenshot 2026-07-07 at 11 09 28 PM" src="https://github.com/user-attachments/assets/f391e5c6-f37c-4778-ac02-25b757653b14" />
<img width="1275" height="883" alt="Screenshot 2026-07-07 at 11 08 07 PM" src="https://github.com/user-attachments/assets/6ba933ef-3760-4308-8d9b-71edb8cbcd3d" />
<img width="1115" height="540" alt="Screenshot 2026-07-07 at 11 06 02 PM" src="https://github.com/user-attachments/assets/c1d90810-eba4-4915-b06d-2a89187d1aee" />
<img width="1031" height="517" alt="Screenshot 2026-07-07 at 11 06 37 PM" src="https://github.com/user-attachments/assets/feb51d9e-35b9-4b0e-b964-ae7c2e269a3e" />




---


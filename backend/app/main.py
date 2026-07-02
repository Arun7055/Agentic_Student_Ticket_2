from fastapi import FastAPI
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import init_db
from app.agent import graph_builder
from app.endpoints import chat, admin, users, tickets, auth

compiled_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_graph
    await init_db()
    
    raw_db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    
    if "?ssl=require" in raw_db_url:
        raw_db_url = raw_db_url.replace("?ssl=require", "?sslmode=require")
    elif "&ssl=require" in raw_db_url:
        raw_db_url = raw_db_url.replace("&ssl=require", "&sslmode=require")

    # Injected connect_timeout=10 to survive Neon DB serverless cold starts
    if "connect_timeout=" not in raw_db_url:
        separator = "&" if "?" in raw_db_url else "?"
        raw_db_url = f"{raw_db_url}{separator}connect_timeout=10"

    # Add 'check=AsyncConnectionPool.check_connection' so Python auto-discards dead Neon sockets
    async with AsyncConnectionPool(
        conninfo=raw_db_url, 
        max_size=10, 
        timeout=10, 
        check=AsyncConnectionPool.check_connection,
        kwargs={"autocommit": True}
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup() 
        compiled_graph = graph_builder.compile(checkpointer=checkpointer)
        
        print("🟢 Ticketing Gateway v2 Online.")
        yield  # <-- THIS HOLDS THE SERVER ACTIVE WHILE RUNNING

app = FastAPI(title="Ticketing Gateway v2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],  # Allows Authorization Bearer tokens
)

@app.get("/", tags=["System"])
def root_status():
    return {"status": "online", "system": "Agentic Ticketing Gateway v2"}

app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(auth.router)
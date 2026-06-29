from fastapi import FastAPI
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os

from app.database import init_db
from app.agent import graph_builder
from app.endpoints import chat, admin  # <-- Notice health is gone!

compiled_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_graph
    print("🚀 Booting up: Syncing SQLModel tables...")
    await init_db()
    
    print("🧠 Booting up: Hooking LangGraph subconscious into Neon DB...")
    raw_db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    
    if "?ssl=require" in raw_db_url:
        raw_db_url = raw_db_url.replace("?ssl=require", "?sslmode=require")
    elif "&ssl=require" in raw_db_url:
        raw_db_url = raw_db_url.replace("&ssl=require", "&sslmode=require")

    async with AsyncConnectionPool(conninfo=raw_db_url, max_size=10, kwargs={"autocommit": True}) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup() 
        
        compiled_graph = graph_builder.compile(checkpointer=checkpointer)
        print("🟢 Brain & Spine fully synchronized.")
        yield

    print("💤 Shutting down...")

app = FastAPI(title="Ticketing Gateway v2", lifespan=lifespan)

# ---> THE REPLACEMENT: Built-in root landing page <---
@app.get("/", tags=["System"])
def root_status():
    return {"status": "online", "system": "Agentic Ticketing Gateway v2"}

# Mount only the business routers
app.include_router(chat.router)
app.include_router(admin.router)
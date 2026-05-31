import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.generate import router as generate_router
from app.routes.tournaments import router as tournaments_router
from app.routes.register import router as register_router
from app.services.rag import get_rag_chunk_by_id, get_rag_status, warm_rag_index

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify the MongoDB connection on startup, then start background warmups."""
    # Establish (and verify) the MongoDB connection up front so failures surface
    # clearly at boot rather than lazily on the first request.
    try:
        await database.connect_to_mongo()
        logger.info("✅ MongoDB connected: %s", database.DB_NAME)
    except Exception as exc:  # noqa: BLE001 — we want to surface any connection failure
        logger.error("❌ MongoDB connection failed: %s", exc)
        if database.MONGODB_STARTUP_REQUIRED:
            # Operators can opt into hard-failing startup when the DB is mandatory.
            raise

    rag_warmup_task = asyncio.create_task(warm_rag_index())
    app.state.rag_warmup_task = rag_warmup_task
    try:
        yield
    finally:
        if not rag_warmup_task.done():
            rag_warmup_task.cancel()
            with suppress(asyncio.CancelledError):
                await rag_warmup_task
        await database.close_mongo_connection()


app = FastAPI(title="Golf Tournament Planner API", lifespan=lifespan)

_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
_allowed_origins = [_frontend_url]
# Always allow local Vite dev server when running locally
if _frontend_url != "http://localhost:5173":
    _allowed_origins.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(generate_router)
app.include_router(tournaments_router)
app.include_router(register_router)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/rag/status")
async def rag_status():
    return get_rag_status()


@app.get("/rag/chunk/{chunk_id}")
async def rag_chunk(chunk_id: str):
    chunk = await get_rag_chunk_by_id(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk

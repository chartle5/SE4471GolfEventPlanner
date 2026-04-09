import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.generate import router as generate_router
from app.routes.tournaments import router as tournaments_router
from app.routes.register import router as register_router
from app.services.rag import get_rag_status, warm_rag_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background warmups without blocking app startup."""
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
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

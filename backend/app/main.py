from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.generate import router as generate_router
from app.routes.tournaments import router as tournaments_router
from app.routes.register import router as register_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to MongoDB on startup and close the connection on shutdown."""
    await database.connect_to_mongo()
    yield
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
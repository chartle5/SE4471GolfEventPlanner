import os

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME: str = os.getenv("MONGODB_DB_NAME", "golf_planner")
MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(
    os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")
)
MONGODB_CONNECT_TIMEOUT_MS = int(
    os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "5000")
)
MONGODB_STARTUP_REQUIRED = (
    os.getenv("MONGODB_STARTUP_REQUIRED", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)

_client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> None:
    global _client
    candidate_client = AsyncIOMotorClient(
        MONGODB_URL,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=MONGODB_SERVER_SELECTION_TIMEOUT_MS,
        connectTimeoutMS=MONGODB_CONNECT_TIMEOUT_MS,
    )
    db = candidate_client[DB_NAME]

    try:
        await candidate_client.admin.command("ping")

        # Create indexes for fast lookups
        await db.tournaments.create_index("tournament_id", unique=True)
        await db.tournaments.create_index("registration_token", unique=True)
        await db.tournaments.create_index("user_id")
        await db.registrations.create_index("tournament_id")
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index("username", unique=True)
    except Exception:
        candidate_client.close()
        raise

    _client = candidate_client


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        try:
            await connect_to_mongo()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Database is unavailable. Please try again later.",
            ) from exc

    if _client is None:
        raise RuntimeError("MongoDB client is not initialised. Ensure connect_to_mongo() ran during app startup.")
    return _client[DB_NAME]

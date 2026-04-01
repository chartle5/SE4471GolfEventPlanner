import os
import ssl

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME: str = os.getenv("MONGODB_DB_NAME", "golf_planner")

_client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> None:
    global _client
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    _client = AsyncIOMotorClient(MONGODB_URL, tls=True, tlsCAFile=certifi.where())
    db = _client[DB_NAME]

    # Create indexes for fast lookups
    await db.tournaments.create_index("tournament_id", unique=True)
    await db.tournaments.create_index("registration_token", unique=True)
    await db.tournaments.create_index("user_id")
    await db.registrations.create_index("tournament_id")
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client is not initialised. Ensure connect_to_mongo() ran during app startup.")
    return _client[DB_NAME]

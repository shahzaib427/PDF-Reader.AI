from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import logging

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = client.get_default_database()
        # Ping to verify connection
        await client.admin.command("ping")
        logger.info("✅ Connected to MongoDB")
        await create_indexes()
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


async def disconnect_db():
    global client
    if client:
        client.close()
        logger.info("MongoDB disconnected")


async def create_indexes():
    """Create indexes for performance."""
    await db.sessions.create_index("session_id", unique=True)
    await db.sessions.create_index("created_at", expireAfterSeconds=86400)  # 24h TTL
    await db.pdfs.create_index("session_id")
    await db.chat_history.create_index("session_id")
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    logger.info("Indexes created")


def get_db():
    return db

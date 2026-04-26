from motor.motor_asyncio import AsyncIOMotorClient
from src.core.config import settings
from src.core.logger import logger

_client: AsyncIOMotorClient = None
_db = None


async def connect_db():
    global _client, _db
    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        _db = _client[settings.mongodb_db_name]
        await _client.admin.command("ping")
        logger.success(f"Connected to MongoDB Atlas: {settings.mongodb_db_name}")
        await _create_indexes()
        await _seed_admin()
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


async def disconnect_db():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_db():
    return _db


async def _create_indexes():
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.analyses.create_index("user_id")
    await db.analyses.create_index("recorded_at")
    logger.debug("MongoDB indexes created")


def _hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def _seed_admin():
    from datetime import datetime, timezone
    db = get_db()

    existing = await db.users.find_one({"username": settings.admin_username})
    if not existing:
        admin_doc = {
            "username": settings.admin_username,
            "email": settings.admin_email,
            "full_name": "System Administrator",
            "mobile": "",
            "hashed_password": _hash_password(settings.admin_password),
            "role": "admin",
            "is_verified": True,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
        }
        await db.users.insert_one(admin_doc)
        logger.success(f"Admin account created: {settings.admin_username}")
    else:
        logger.debug(f"Admin account already exists: {settings.admin_username}")
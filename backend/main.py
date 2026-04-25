import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import connect_db, disconnect_db
from routes import auth, upload, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="PDF Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health():
    from database import db
    try:
        await db.command("ping")
        mongo_status = "connected"
    except Exception:
        mongo_status = "disconnected"
    return {
        "status": "ok",
        "mongodb": mongo_status,
        "ai_configured": bool(settings.OPENROUTER_API_KEY and len(settings.OPENROUTER_API_KEY) > 20),
    }


if __name__ == "__main__":
    import uvicorn
    # ✅ reload=False — fixes Windows multiprocessing/platform.py crash
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
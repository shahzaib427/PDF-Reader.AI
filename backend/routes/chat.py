import re
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from database import get_db
from models.schemas import ChatRequest, SetNameRequest, ClearChatRequest
from utils.pdf_utils import find_relevant_chunks
from utils.ai_service import answer_question
from routes.auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)

NAME_PATTERNS = [
    re.compile(r"my name is ([a-zA-Z]+)", re.I),
    re.compile(r"i(?:'m| am) ([a-zA-Z]+)", re.I),
    re.compile(r"call me ([a-zA-Z]+)", re.I),
    re.compile(r"^([a-zA-Z]+)$", re.I),
    re.compile(r"name[:\s]+([a-zA-Z]+)", re.I),
]

NAME_QUERIES = [
    "what is my name",
    "what's my name",
    "do you know my name",
    "remember my name",
    "who am i",
    "tell me my name",
]


def detect_name(message: str):
    if len(message) > 80:
        return None
    for pattern in NAME_PATTERNS:
        m = pattern.search(message)
        if m:
            return m.group(1).capitalize()
    return None


def is_name_query(message: str) -> bool:
    lower = message.lower().strip()
    return any(q in lower for q in NAME_QUERIES)


def is_summary_request(message: str) -> bool:
    lower = message.lower()
    return any(w in lower for w in ["summarize", "summary", "overview", "briefly explain", "what is this document"])


# POST /api/chat
@router.post("")
async def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    db = get_db()

    # Ensure session
    session = await db.sessions.find_one({"session_id": req.session_id})
    if not session:
        session = {
            "session_id": req.session_id,
            "user_id": str(current_user["_id"]) if current_user else None,
            "user_name": None,
            "active_pdf_id": None,
            "created_at": datetime.utcnow(),
        }
        await db.sessions.insert_one(session)

    # Detect name
    extracted_name = detect_name(req.message)
    if extracted_name:
        await db.sessions.update_one(
            {"session_id": req.session_id},
            {"$set": {"user_name": extracted_name}},
        )
        session["user_name"] = extracted_name

    # Ensure chat history doc
    chat_doc = await db.chat_history.find_one({"session_id": req.session_id})
    if not chat_doc:
        chat_doc = {
            "session_id": req.session_id,
            "user_id": str(current_user["_id"]) if current_user else None,
            "pdf_id": req.pdf_id or session.get("active_pdf_id"),
            "messages": [],
        }
        await db.chat_history.insert_one(chat_doc)

    messages = chat_doc.get("messages", [])
    user_name = session.get("user_name")

    # --- Build reply ---
    reply = ""

    if is_name_query(req.message):
        if user_name:
            reply = f"Your name is **{user_name}**! I remembered it from when you introduced yourself. 😊"
        else:
            reply = (
                "I don't know your name yet! You can tell me anytime by saying "
                "'My name is Alex' and I'll remember it for our conversation."
            )
    else:
        active_pdf_id = req.pdf_id or session.get("active_pdf_id")
        if not active_pdf_id:
            greeting = f"Hi {user_name}! " if user_name else ""
            reply = (
                f"{greeting}Please upload a PDF document first, "
                "then I can help you with summaries and questions about its content. 📄"
            )
        else:
            try:
                pdf = await db.pdfs.find_one(
                    {"_id": ObjectId(active_pdf_id)},
                    {"chunks": 1, "short_summary": 1, "detailed_summary": 1, "file_name": 1, "summary_generated": 1},
                )
            except Exception:
                pdf = None

            if not pdf:
                reply = "I couldn't find the associated PDF. Please re-upload your document."
            elif is_summary_request(req.message):
                if pdf.get("summary_generated"):
                    reply = (
                        f"**Summary of \"{pdf['file_name']}\":**\n\n"
                        f"**Short Summary:**\n{pdf['short_summary']}\n\n"
                        f"**Detailed Summary:**\n{pdf['detailed_summary']}"
                    )
                else:
                    reply = "The summary is still being generated. Please wait a moment and try again!"
            else:
                relevant = find_relevant_chunks(pdf.get("chunks", []), req.message, top_k=3)
                reply = await answer_question(req.message, relevant, user_name, messages)

    # Persist messages to DB
    now = datetime.utcnow()
    new_messages = [
        {"role": "user", "content": req.message, "timestamp": now},
        {"role": "assistant", "content": reply, "timestamp": now},
    ]
    await db.chat_history.update_one(
        {"session_id": req.session_id},
        {
            "$push": {"messages": {"$each": new_messages}},
            "$set": {"pdf_id": req.pdf_id or session.get("active_pdf_id"), "updated_at": now},
        },
        upsert=True,
    )

    return {
        "reply": reply,
        "user_name": user_name,
        "message_count": len(messages) + 2,
    }


# GET /api/chat/history
@router.get("/history")
async def get_history(session_id: str):
    db = get_db()
    chat = await db.chat_history.find_one({"session_id": session_id})
    if not chat:
        return {"messages": [], "pdf": None, "session_id": session_id}

    pdf = None
    if chat.get("pdf_id"):
        try:
            pdf_doc = await db.pdfs.find_one(
                {"_id": ObjectId(chat["pdf_id"])},
                {"file_name": 1, "page_count": 1},
            )
            if pdf_doc:
                pdf = {"pdf_id": chat["pdf_id"], "file_name": pdf_doc["file_name"], "page_count": pdf_doc.get("page_count")}
        except Exception:
            pass

    messages = []
    for m in chat.get("messages", []):
        messages.append(
            {
                "role": m["role"],
                "content": m["content"],
                "timestamp": m.get("timestamp", datetime.utcnow()).isoformat(),
            }
        )

    return {"messages": messages, "pdf": pdf, "session_id": session_id}


# DELETE /api/chat/clear
@router.delete("/clear")
async def clear_chat(req: ClearChatRequest):
    db = get_db()
    await db.chat_history.update_one(
        {"session_id": req.session_id},
        {"$set": {"messages": []}},
    )
    return {"success": True, "message": "Chat cleared"}


# GET /api/chat/session-info
@router.get("/session-info")
async def session_info(session_id: str):
    db = get_db()
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        return {"user_name": None, "active_pdf": None}

    active_pdf = None
    if session.get("active_pdf_id"):
        try:
            pdf = await db.pdfs.find_one(
                {"_id": ObjectId(session["active_pdf_id"])},
                {"file_name": 1, "page_count": 1, "summary_generated": 1, "short_summary": 1},
            )
            if pdf:
                active_pdf = {
                    "pdf_id": session["active_pdf_id"],
                    "file_name": pdf["file_name"],
                    "page_count": pdf.get("page_count"),
                    "summary_generated": pdf.get("summary_generated", False),
                    "short_summary": pdf.get("short_summary"),
                }
        except Exception:
            pass

    return {"user_name": session.get("user_name"), "active_pdf": active_pdf}


# POST /api/chat/set-name
@router.post("/set-name")
async def set_name(req: SetNameRequest):
    db = get_db()
    await db.sessions.update_one(
        {"session_id": req.session_id},
        {"$set": {"user_name": req.name.strip().capitalize(), "created_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"success": True, "user_name": req.name.strip().capitalize()}

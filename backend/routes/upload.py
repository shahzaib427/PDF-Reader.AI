import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId

from database import get_db
from config import settings
from utils.pdf_utils import (
    extract_text_pdfplumber,
    clean_text,
    chunk_text,
    prepare_chunks_for_db,
)
from utils.ai_service import generate_summaries
from routes.auth import get_current_user

router = APIRouter(prefix="/api/upload-pdf", tags=["pdf"])
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("")
async def upload_pdf(
    pdf: UploadFile = File(...),
    session_id: str = Form(...),
    current_user=Depends(get_current_user),
):
    db = get_db()

    # Validate type
    if pdf.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files are allowed")

    file_bytes = await pdf.read()
    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(400, f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB")

    # Extract text
    try:
        raw_text, page_count = extract_text_pdfplumber(file_bytes)
    except Exception as e:
        raise HTTPException(500, f"Failed to parse PDF: {e}")

    if not raw_text or len(raw_text.strip()) < 50:
        raise HTTPException(
            400,
            "Could not extract text from this PDF. It may be scanned or image-based.",
        )

    cleaned = clean_text(raw_text)
    raw_chunks = chunk_text(cleaned, settings.CHUNK_SIZE_WORDS, settings.CHUNK_OVERLAP_WORDS)
    chunks = prepare_chunks_for_db(raw_chunks)

    user_id = str(current_user["_id"]) if current_user else None

    # Ensure session exists
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        await db.sessions.insert_one(
            {
                "session_id": session_id,
                "user_id": user_id,
                "user_name": None,
                "active_pdf_id": None,
                "created_at": datetime.utcnow(),
            }
        )

    # Save PDF record
    pdf_doc = {
        "session_id": session_id,
        "user_id": user_id,
        "file_name": pdf.filename,
        "file_size": len(file_bytes),
        "page_count": page_count,
        "full_text": cleaned[:50000],
        "chunks": chunks,
        "short_summary": None,
        "detailed_summary": None,
        "summary_generated": False,
        "uploaded_at": datetime.utcnow(),
    }
    result = await db.pdfs.insert_one(pdf_doc)
    pdf_id = str(result.inserted_id)

    # Update session's active PDF
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"active_pdf_id": pdf_id}},
    )

    # Clear old chat messages for new PDF context
    await db.chat_history.update_one(
        {"session_id": session_id},
        {"$set": {"pdf_id": pdf_id, "messages": []}},
        upsert=True,
    )

    # Generate summaries in background (non-blocking)
    asyncio.create_task(_generate_summaries_bg(pdf_id, cleaned, db))

    return {
        "success": True,
        "pdf_id": pdf_id,
        "file_name": pdf.filename,
        "page_count": page_count,
        "chunk_count": len(chunks),
        "message": "PDF processed. Summaries are being generated in the background.",
    }


async def _generate_summaries_bg(pdf_id: str, text: str, db):
    """Background task: generate and store AI summaries."""
    try:
        summaries = await generate_summaries(text)
        await db.pdfs.update_one(
            {"_id": ObjectId(pdf_id)},
            {
                "$set": {
                    "short_summary": summaries["short_summary"],
                    "detailed_summary": summaries["detailed_summary"],
                    "summary_generated": True,
                }
            },
        )
        logger.info(f"Summaries generated for PDF {pdf_id}")
    except Exception as e:
        logger.error(f"Background summary error for {pdf_id}: {e}")


@router.get("/{pdf_id}/summary")
async def get_summary(pdf_id: str):
    db = get_db()
    try:
        pdf = await db.pdfs.find_one(
            {"_id": ObjectId(pdf_id)},
            {
                "file_name": 1,
                "page_count": 1,
                "summary_generated": 1,
                "short_summary": 1,
                "detailed_summary": 1,
            },
        )
    except Exception:
        raise HTTPException(400, "Invalid PDF ID")

    if not pdf:
        raise HTTPException(404, "PDF not found")

    return {
        "pdf_id": pdf_id,
        "file_name": pdf["file_name"],
        "page_count": pdf["page_count"],
        "summary_generated": pdf.get("summary_generated", False),
        "short_summary": pdf.get("short_summary"),
        "detailed_summary": pdf.get("detailed_summary"),
    }


@router.get("/session/{session_id}")
async def get_session_pdfs(session_id: str):
    db = get_db()
    cursor = db.pdfs.find(
        {"session_id": session_id},
        {"file_name": 1, "file_size": 1, "page_count": 1, "uploaded_at": 1, "summary_generated": 1, "short_summary": 1},
    ).sort("uploaded_at", -1)
    pdfs = []
    async for doc in cursor:
        pdfs.append(
            {
                "pdf_id": str(doc["_id"]),
                "file_name": doc["file_name"],
                "file_size": doc.get("file_size"),
                "page_count": doc.get("page_count"),
                "uploaded_at": doc.get("uploaded_at"),
                "summary_generated": doc.get("summary_generated", False),
                "short_summary": doc.get("short_summary"),
            }
        )
    return pdfs

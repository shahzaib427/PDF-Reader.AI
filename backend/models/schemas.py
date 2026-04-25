from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user: dict


# ── Session ───────────────────────────────────────────────────────────────────

class SetNameRequest(BaseModel):
    session_id: str
    name: str


class SessionInfoResponse(BaseModel):
    session_id: str
    user_name: Optional[str]
    active_pdf_id: Optional[str]
    active_pdf_name: Optional[str]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str
    pdf_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatResponse(BaseModel):
    reply: str
    user_name: Optional[str]
    message_count: int


class HistoryResponse(BaseModel):
    messages: List[dict]
    pdf: Optional[dict]
    session_id: str


# ── PDF ───────────────────────────────────────────────────────────────────────

class PDFSummaryResponse(BaseModel):
    pdf_id: str
    file_name: str
    page_count: int
    chunk_count: int
    summary_generated: bool
    short_summary: Optional[str]
    detailed_summary: Optional[str]


class ClearChatRequest(BaseModel):
    session_id: str

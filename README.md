# 📜 Folio — AI PDF Chatbot

A full-stack AI-powered PDF chatbot with a Python (FastAPI) backend and React frontend.
Chat with your documents using free AI models. No paid APIs required.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 📄 PDF Upload | Drag & drop, up to 5 MB, pdfplumber parsing |
| 🤖 AI Summaries | Short + detailed, generated in background |
| 💬 Contextual Q&A | Answers only from PDF content, chunked retrieval |
| 🧠 Name Memory | Remembers your name across the session |
| 💾 Chat Persistence | Full history saved in MongoDB, survives page reload |
| 🔐 JWT Auth | Optional login, links history to user account |
| 📚 Multi-PDF | Upload multiple PDFs, switch between them |
| 🆓 Free AI | OpenRouter free tier (Mistral 7B, LLaMA 3 8B) |

---

## 🗂 Project Structure

```
pdf-chatbot-py/
├── backend/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # Motor async MongoDB client
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── routes/
│   │   ├── auth.py          # POST /api/auth/register|login, GET /me
│   │   ├── upload.py        # POST /api/upload-pdf, GET /summary, /session
│   │   └── chat.py          # POST /api/chat, GET /history, DELETE /clear
│   └── utils/
│       ├── pdf_utils.py     # pdfplumber, chunking, keyword search
│       └── ai_service.py    # OpenRouter + HuggingFace integration
└── frontend/
    ├── package.json
    ├── public/index.html
    └── src/
        ├── App.js            # Main layout + state
        ├── index.css         # Full design system (warm editorial)
        ├── index.js
        ├── components/
        │   ├── UploadZone.js
        │   ├── SummaryPanel.js
        │   ├── MessageBubble.js
        │   └── AuthModal.js
        ├── hooks/
        │   └── useSession.js
        └── utils/
            └── api.js        # Axios wrappers for all endpoints
```

---

## ⚙️ Setup

### 1. Get a Free AI API Key

Go to **https://openrouter.ai** → Sign up (free) → Create an API key.
Free models include Mistral 7B and LLaMA 3 8B — no credit card needed.

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env:  set MONGODB_URI and OPENROUTER_API_KEY

# Start server
python main.py
# → http://localhost:8000
# → Docs: http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
npm install
npm start
# → http://localhost:3000
```

### 4. MongoDB

**Local:**
```bash
mongod --dbpath /data/db
# URI: mongodb://localhost:27017/pdf_chatbot
```

**Atlas (free tier):**
Set `MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/pdf_chatbot`

---

## 🔌 REST API

### Auth
| Method | Endpoint | Body |
|--------|----------|------|
| POST | `/api/auth/register` | `{username, email, password, display_name?}` |
| POST | `/api/auth/login` | `{email, password}` |
| GET | `/api/auth/me` | — (Bearer token) |

### PDF
| Method | Endpoint | |
|--------|----------|-|
| POST | `/api/upload-pdf` | `multipart/form-data: pdf + session_id` |
| GET | `/api/upload-pdf/{id}/summary` | Get summaries (polls until ready) |
| GET | `/api/upload-pdf/session/{sid}` | List PDFs for session |

### Chat
| Method | Endpoint | Body |
|--------|----------|------|
| POST | `/api/chat` | `{session_id, message, pdf_id?}` |
| GET | `/api/chat/history?session_id=` | Full chat history |
| DELETE | `/api/chat/clear` | `{session_id}` |
| GET | `/api/chat/session-info?session_id=` | Name + active PDF |
| POST | `/api/chat/set-name` | `{session_id, name}` |

---

## 🤖 AI Architecture

```
User question
     │
     ▼
 detect_name() ──yes──► store in MongoDB Session
 is_name_query() ──yes──► return stored name
 is_summary_request() ──yes──► return cached summary
     │
     ▼
 find_relevant_chunks()
   keyword scoring (no vector DB)
   top-3 chunks selected
     │
     ▼
 answer_question()
   → OpenRouter (Mistral 7B free)
   → HuggingFace fallback
     │
     ▼
 save to chat_history (MongoDB)
     │
     ▼
 return reply + persist
```

**PDF chunking:** 800-word chunks with 100-word overlap
**Retrieval:** keyword frequency scoring — fast, zero dependencies
**Context window:** last 6 messages included for conversation memory

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, custom CSS (no Tailwind CDN needed) |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Database | MongoDB, Motor (async) |
| PDF | pdfplumber + PyPDF2 fallback |
| AI | OpenRouter (Mistral 7B free) + HuggingFace |
| Auth | JWT (python-jose) + bcrypt |
| HTTP | Axios (frontend), httpx (backend) |

---

## 🔑 Environment Variables

```env
PORT=8000
MONGODB_URI=mongodb://localhost:27017/pdf_chatbot
JWT_SECRET=long-random-secret-here
OPENROUTER_API_KEY=sk-or-v1-...
HUGGINGFACE_API_KEY=hf_...          # optional fallback
MAX_FILE_SIZE_MB=5
CHUNK_SIZE_WORDS=800
CHUNK_OVERLAP_WORDS=100
ALLOWED_ORIGINS=http://localhost:3000
```

---

## 💡 Performance Notes

- PDF text capped at 50,000 characters stored per document
- Only top-3 relevant chunks sent to AI per query (~2400 words)
- Summaries generated asynchronously via `asyncio.create_task`
- Session TTL: 24 hours (MongoDB TTL index)
- Works comfortably on 4 GB RAM — no local model loading

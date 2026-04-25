"""
PDF parsing, chunking, and keyword-based retrieval utilities.
No vector database required — pure keyword scoring.
"""
import re
import logging
from typing import List, Dict, Tuple
import io

logger = logging.getLogger(__name__)

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "it", "this", "that", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "i", "you", "he", "she",
    "we", "they", "them", "their", "our", "your", "his", "her", "its",
    "what", "which", "who", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "not",
    "only", "same", "so", "than", "too", "very", "just", "as", "from",
    "by", "about", "into", "through", "during", "before", "after", "if",
    "then", "there", "here", "these", "those", "can", "need", "shall",
}


def extract_text_pdfplumber(file_bytes: bytes) -> Tuple[str, int]:
    """Extract text using pdfplumber (preferred — handles tables well)."""
    try:
        import pdfplumber
        text_parts = []
        page_count = 0
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts), page_count
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}, trying PyPDF2")
        return extract_text_pypdf2(file_bytes)


def extract_text_pypdf2(file_bytes: bytes) -> Tuple[str, int]:
    """Fallback: extract text using PyPDF2."""
    import PyPDF2
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    page_count = len(reader.pages)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts), page_count


def clean_text(text: str) -> str:
    """Normalize extracted PDF text."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Remove non-printable chars except newlines
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def extract_keywords(text: str, top_n: int = 20) -> List[str]:
    """Extract top-N keywords by frequency, excluding stopwords."""
    words = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    freq: Dict[str, int] = {}
    for w in words:
        if len(w) > 3 and w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]


def find_relevant_chunks(
    chunks: List[Dict], query: str, top_k: int = 3
) -> List[str]:
    """
    Score chunks by keyword overlap with query.
    Returns top_k chunk texts, ordered by relevance.
    """
    query_words = set(
        w
        for w in re.sub(r"[^a-z0-9\s]", " ", query.lower()).split()
        if len(w) > 2 and w not in STOPWORDS
    )

    if not query_words:
        return [c["text"] for c in chunks[:top_k]]

    scored = []
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        score = 0
        for word in query_words:
            count = text_lower.count(word)
            score += count
            if word in text_lower:
                score += 2  # bonus for presence
        scored.append((score, chunk["text"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]


def prepare_chunks_for_db(chunks: List[str]) -> List[Dict]:
    """Build chunk documents for MongoDB storage."""
    result = []
    for i, text in enumerate(chunks):
        result.append(
            {
                "index": i,
                "text": text,
                "keywords": extract_keywords(text),
            }
        )
    return result

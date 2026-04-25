"""
AI service — OpenRouter (free) + HuggingFace fallback
"""
import json
import logging
import httpx
from typing import List, Dict, Optional
from config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
HF_BASE = "https://api-inference.huggingface.co/models"

# ✅ Updated free model list for OpenRouter 2025
FREE_MODELS = [
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-2-9b-it:free",
    "openchat/openchat-7b:free",
    "mistralai/mistral-7b-instruct",           # non-free fallback names
    "openai/gpt-3.5-turbo",
]

# HuggingFace models to try in order
HF_MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "mistralai/Mistral-7B-Instruct-v0.2",
    "HuggingFaceH4/zephyr-7b-beta",
    "microsoft/phi-2",
]


def _is_key_set(key: str) -> bool:
    return bool(key and len(key) > 20 and "your" not in key and "token" not in key.lower())


async def _call_openrouter(messages: List[Dict], system_prompt: str = "", max_tokens: int = 700) -> str:
    api_key = settings.OPENROUTER_API_KEY
    if not _is_key_set(api_key):
        raise ValueError("OpenRouter API key not configured")

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    last_error = None
    for model in FREE_MODELS:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    f"{OPENROUTER_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "PDF Chatbot",
                    },
                    json={
                        "model": model,
                        "messages": full_messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    logger.info(f"OpenRouter success with model: {model}")
                    return content
                else:
                    body = resp.text[:150]
                    logger.warning(f"OpenRouter {model}: {resp.status_code} — {body}")
                    last_error = f"{resp.status_code}"
        except Exception as e:
            logger.warning(f"OpenRouter {model} exception: {e}")
            last_error = str(e)

    raise Exception(f"All OpenRouter models failed")


async def _call_huggingface(prompt: str, max_tokens: int = 500) -> str:
    api_key = settings.HUGGINGFACE_API_KEY
    if not _is_key_set(api_key):
        raise ValueError("HuggingFace API key not set")

    last_error = None
    for model in HF_MODELS:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{HF_BASE}/{model}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "max_new_tokens": max_tokens,
                            "temperature": 0.3,
                            "return_full_text": False,
                            "do_sample": True,
                        },
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        text = data[0].get("generated_text", "").strip()
                        if text:
                            logger.info(f"HuggingFace success with model: {model}")
                            return text
                elif resp.status_code == 503:
                    # Model loading — skip to next
                    logger.warning(f"HF {model} loading (503), trying next...")
                    last_error = "Model loading"
                else:
                    logger.warning(f"HF {model}: {resp.status_code} — {resp.text[:100]}")
                    last_error = str(resp.status_code)
        except Exception as e:
            logger.warning(f"HF {model} exception: {e}")
            last_error = str(e)

    raise Exception(f"All HuggingFace models failed: {last_error}")


async def _call_ai(messages: List[Dict], system_prompt: str = "", max_tokens: int = 700) -> str:
    """Try OpenRouter first, then HuggingFace."""
    # Try OpenRouter
    if _is_key_set(settings.OPENROUTER_API_KEY):
        try:
            return await _call_openrouter(messages, system_prompt, max_tokens)
        except Exception as e:
            logger.error(f"OpenRouter failed: {e}")

    # Try HuggingFace
    if _is_key_set(settings.HUGGINGFACE_API_KEY):
        try:
            # Convert messages to a single prompt for HF
            prompt_parts = []
            if system_prompt:
                prompt_parts.append(f"[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n")
            for m in messages:
                if m["role"] == "user":
                    prompt_parts.append(f"{m['content']} [/INST]")
                elif m["role"] == "assistant":
                    prompt_parts.append(f"{m['content']} [INST] ")
            prompt = "".join(prompt_parts)
            return await _call_huggingface(prompt, max_tokens)
        except Exception as e:
            logger.error(f"HuggingFace failed: {e}")

    raise Exception("No AI service configured")


async def generate_summaries(pdf_text: str) -> Dict[str, str]:
    truncated = pdf_text[:5000]

    system_prompt = (
        "You are a document summarizer. "
        'Respond ONLY with this exact JSON format — no markdown, no extra text: '
        '{"shortSummary":"2-3 sentence overview","detailedSummary":"5-8 sentence detailed summary"}'
    )
    messages = [{"role": "user", "content": f"Summarize this document:\n\n{truncated}"}]

    try:
        raw = await _call_ai(messages, system_prompt, max_tokens=500)
        logger.info(f"Summary raw response (first 200): {raw[:200]}")

        # Try JSON parse
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw[start:end])
                short = parsed.get("shortSummary") or parsed.get("short_summary") or ""
                detailed = parsed.get("detailedSummary") or parsed.get("detailed_summary") or ""
                if short and detailed:
                    return {"short_summary": short, "detailed_summary": detailed}
            except json.JSONDecodeError:
                pass

        # Fallback: use the raw text as both summaries
        clean = raw.strip()
        sentences = [s.strip() for s in clean.replace("\n", " ").split(".") if len(s.strip()) > 20]
        short = ". ".join(sentences[:3]) + "." if sentences else clean[:300]
        detailed = clean if len(clean) > 100 else short
        return {"short_summary": short, "detailed_summary": detailed}

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        hf_set = _is_key_set(settings.HUGGINGFACE_API_KEY)
        or_set = _is_key_set(settings.OPENROUTER_API_KEY)
        if not hf_set:
            msg = "⚠️ AI not configured. Add HUGGINGFACE_API_KEY to .env — get free token at https://huggingface.co/settings/tokens"
        elif not or_set:
            msg = "⚠️ Add OPENROUTER_API_KEY to .env for better AI. Get free key at https://openrouter.ai"
        else:
            msg = f"⚠️ AI request failed: {str(e)[:100]}. Both services tried."
        return {"short_summary": msg, "detailed_summary": msg}


async def answer_question(
    question: str,
    context_chunks: List[str],
    user_name: Optional[str],
    chat_history: List[Dict],
) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    user_ref = f"The user's name is {user_name}." if user_name else ""

    system_prompt = (
        f"You are a helpful PDF assistant. {user_ref} "
        "Answer ONLY based on the provided PDF context. "
        "If the answer is not in the context, say: 'I couldn't find that in the PDF.' "
        "Be concise and accurate."
    )

    recent = chat_history[-6:]
    messages = [
        *[{"role": m["role"], "content": m["content"]} for m in recent],
        {"role": "user", "content": f"PDF Context:\n{context}\n\nQuestion: {question}"},
    ]

    try:
        return await _call_ai(messages, system_prompt, max_tokens=600)
    except Exception as e:
        logger.error(f"Q&A failed: {e}")
        hf_set = _is_key_set(settings.HUGGINGFACE_API_KEY)
        if not hf_set:
            return "⚠️ Add HUGGINGFACE_API_KEY to .env — get free token at https://huggingface.co/settings/tokens"
        return f"⚠️ AI request failed. Both OpenRouter and HuggingFace were tried. Error: {str(e)[:80]}"
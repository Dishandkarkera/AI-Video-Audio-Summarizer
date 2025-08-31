import httpx, json
from app.core.config import get_settings

settings = get_settings()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
HEADERS = {"Content-Type": "application/json"}

async def call_gemini(prompt: str):
    params = {"key": settings.gemini_api_key}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(GEMINI_API_URL, params=params, json=body, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        try:
            return data['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            return str(data)

SUMMARY_SYSTEM_PROMPT = """You are an assistant producing JSON.
Return JSON with keys: summary_short, summary_detailed, highlights (array), sentiment (one of positive|negative|neutral), action_points (array)."""

async def summarize_transcript(transcript: str):
    prompt = f"{SUMMARY_SYSTEM_PROMPT}\nTranscript:\n{transcript[:15000]}\n"  # truncate to avoid overlength
    raw = await call_gemini(prompt)
    # attempt to parse JSON inside response
    import re, json
    match = re.search(r"\{[\s\S]*\}$", raw.strip())
    if match:
        txt = match.group(0)
        try:
            return json.loads(txt)
        except Exception:
            pass
    # fallback structure
    return {
        "summary_short": raw[:200],
        "summary_detailed": raw,
        "highlights": [],
        "sentiment": "neutral",
        "action_points": []
    }

async def chat_with_context(transcript: str, message: str):
    prompt = f"You answer questions about the following transcript. Keep answers grounded.\nTranscript (may be truncated):\n{transcript[:15000]}\nUser question: {message}"
    return await call_gemini(prompt)

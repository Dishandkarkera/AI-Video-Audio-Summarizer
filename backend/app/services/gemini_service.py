import httpx, os, json, re
from typing import List, Dict
from app.core.config import get_settings
from .storage_access import load_transcript
from pathlib import Path

CACHE_DIR = Path('storage')

settings = get_settings()
GEMINI_KEY = settings.gemini_api_key
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent'

SUMMARY_SYSTEM = (
    'Return strict JSON with keys: summary_short, summary_detailed, key_highlights (array), sentiment (positive|negative|neutral), action_points (array).'
)

async def translate_transcript(text: str, target_lang: str = 'hi') -> str:
    """Translate transcript text into target language using Gemini; fallback to original if key missing.

    target_lang: ISO code like 'hi' (Hindi). Returns plain translated text only (no extra notes).
    """
    if not text:
        return ''
    # Quick short-circuit if already asking for English
    if target_lang.lower() in ('en','eng','english'):
        return text
    prompt = (
        f"Translate the following transcript into {target_lang} (natural, conversational).\n"
        "Preserve meaning, names, numbers. Output ONLY the translated text, no preface.\n\n"
        f"Transcript:\n{text[:15000]}"
    )
    try:
        raw = await call_gemini(prompt)
        # Strip potential code fences or labels
        cleaned = raw.strip().replace('```','').strip()
        return cleaned
    except Exception:
        # fallback: return original with marker
        return text

# ---- On-demand translation detection (chat trigger) ----

LANG_NAME_TO_CODE = {
    'hindi': 'hi', 'spanish': 'es', 'french': 'fr', 'german': 'de', 'chinese': 'zh', 'mandarin': 'zh',
    'japanese': 'ja', 'korean': 'ko', 'italian': 'it', 'portuguese': 'pt', 'russian': 'ru',
    'arabic': 'ar', 'bengali': 'bn', 'marathi': 'mr', 'tamil': 'ta', 'telugu': 'te', 'urdu': 'ur',
    'indonesian': 'id', 'turkish': 'tr', 'polish': 'pl', 'dutch': 'nl', 'thai': 'th', 'vietnamese': 'vi'
}

_LANG_PATTERN = re.compile(r"(?:(?:in|to|into)\s+)?(" + '|'.join(re.escape(k) for k in LANG_NAME_TO_CODE.keys()) + r")\b", re.IGNORECASE)

def _detect_translation_request(question: str) -> str | None:
    """Return target language code if the question is a translation request, else None."""
    ql = question.lower()
    # Heuristics: mentions 'transcript' or 'translate' or 'give/show/provide ... in <lang>'
    if any(k in ql for k in ['translate', 'translation', 'transcript in', 'give me the transcript', 'show transcript', 'provide transcript']):
        m = _LANG_PATTERN.search(ql)
        if m:
            name = m.group(1).lower()
            return LANG_NAME_TO_CODE.get(name)
    # Simpler pattern: ends with 'in <lang>' referencing 'transcript'
    if 'transcript' in ql:
        m = _LANG_PATTERN.search(ql)
        if m:
            return LANG_NAME_TO_CODE.get(m.group(1).lower())
    return None

async def maybe_handle_translation(media_id: str, question: str):
    """If question asks for transcript translation, perform it and return answer dict, else None."""
    target_code = _detect_translation_request(question)
    if not target_code:
        return None
    data = load_transcript(media_id)
    if not data:
        return {"answer": "Transcript not found.", "references": []}
    text = data.get('text') or ' '.join(s.get('text','') for s in data.get('segments', []))
    translated = await translate_transcript(text, target_code)
    lang_name = next((n.title() for n,c in LANG_NAME_TO_CODE.items() if c==target_code), target_code)
    prefix = f"Transcript translated to {lang_name}:\n\n"
    answer = prefix + translated[:60000]
    usage = _build_usage(question, answer, extra_context=len(text[:4000]))
    return {"answer": answer, "references": [], "usage": usage}

async def call_gemini(prompt: str) -> str:
    if not GEMINI_KEY:
        # fallback deterministic placeholder (non-secret path)
        return '{"summary_short":"No API key set","summary_detailed":"Configure GEMINI_API_KEY.","key_highlights":[],"sentiment":"neutral","action_points":[]}'
    async with httpx.AsyncClient(timeout=60) as client:
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        r = await client.post(GEMINI_URL, params={'key': GEMINI_KEY}, json=body)
        r.raise_for_status()
        data = r.json()
        try:
            return data['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            return json.dumps(data)

async def call_gemini_summarize(transcript: str, level: str = 'short') -> dict:
    truncated = transcript[:15000]
    prompt = f"{SUMMARY_SYSTEM}\nTranscript:\n{truncated}\nLevel: {level}"\
        [:18000]
    raw = await call_gemini(prompt)
    # --- Cleanup: strip code fences and extract JSON if present ---
    cleaned = raw.strip()
    # Remove fenced code blocks ```json ... ``` or ``` ... ```
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'```$', '', cleaned).strip()
    # Some models return text like: ```json { ... } ``` or prefix text then JSON
    # Try to locate the first '{' and the matching last '}' to parse object.
    json_obj = None
    brace_match = re.search(r'\{[\s\S]*\}', cleaned)
    if brace_match:
        candidate = brace_match.group(0)
        try:
            json_obj = json.loads(candidate)
        except Exception:
            json_obj = None
    if json_obj and isinstance(json_obj, dict):
        # Normalize keys expected by UI
        json_obj.setdefault('summary_short', json_obj.get('short') or '')
        json_obj.setdefault('summary_detailed', json_obj.get('detailed') or json_obj.get('summary') or '')
        json_obj.setdefault('key_highlights', json_obj.get('highlights') or [])
        json_obj.setdefault('action_points', json_obj.get('actionPoints') or [])
        json_obj.setdefault('sentiment', json_obj.get('tone') or 'neutral')
        return json_obj
    # If not JSON, build a structured fallback using the cleaned text
    return {
        'summary_short': cleaned[:300],
        'summary_detailed': cleaned[:4000],
        'key_highlights': [],
        'sentiment': 'neutral',
        'action_points': []
    }

async def get_summary(media_id: str):
    cache_file = CACHE_DIR / f"{media_id}_summary.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    data = load_transcript(media_id)
    if not data:
        return {'error': 'Transcript not found'}
    result = await call_gemini_summarize(data.get('text',''))
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass
    return result

async def call_gemini_chat(segments: List[Dict], question: str) -> Dict:
    # Build a trimmed context of top segments by naive keyword overlap
    terms = [t for t in question.lower().split() if len(t) > 2]
    scored = []
    for seg in segments:
        text = seg.get('text','')
        lt = text.lower()
        score = sum(lt.count(t) for t in terms)
        if score:
            scored.append((score, seg))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:8]] or segments[:4]
    context = "\n".join([f"[{s.get('start'):.1f}-{s.get('end'):.1f}] {s.get('text')}" for s in top])
    prompt = f"Answer the user question STRICTLY using the transcript context. Cite timestamps in brackets.\nQuestion: {question}\nContext:\n{context}\nAnswer:"
    raw = await call_gemini(prompt)
    refs = [{"start": s.get('start'), "end": s.get('end'), "text": s.get('text','')} for s in top[:5]]
    return {"text": raw, "references": refs}

async def chat(media_id: str, question: str, user: dict):
    # Translation shortcut
    trans = await maybe_handle_translation(media_id, question)
    if trans:
        return trans
    data = load_transcript(media_id)
    if not data:
        return {"answer": "Transcript not found.", "references": []}
    segs = data.get('segments', []) or []
    # --- Pseudo segmentation fallback if real timestamps are absent ---
    # If there are no segments OR segments lack usable start values, fabricate lightweight segments from the raw text.
    if (not segs or all(s.get('start') in (None, 0) for s in segs)):
        raw_text = (data.get('text') or '').strip()
        if raw_text:
            # Split into sentences (very lightweight heuristic).
            import re as _re
            parts = [p.strip() for p in _re.split(r'(?<=[.!?])\s+', raw_text) if p.strip()]
            if parts:
                # Assume an average 5s per sentence for synthetic timing.
                synthetic = []
                for i, sent in enumerate(parts[:120]):  # cap to avoid explosion
                    start_t = i * 5.0
                    synthetic.append({'start': start_t, 'end': start_t + 5.0, 'text': sent})
                segs = synthetic
                # Do not mutate original data on disk, just in-memory for chat retrieval.
    response = await call_gemini_chat(segs, question)
    answer = response.get('text','')
    # If model did not include any [mm:ss] style timestamps but we have references, append them inline at end for clarity
    if '[' not in answer and response.get('references'):
        def fmt(t):
            try:
                mm = int(float(t)//60); ss = int(float(t)%60); return f"{mm:02d}:{ss:02d}"
            except Exception:
                return "??:??"
        ref_str = ', '.join(f"[{fmt(r.get('start'))}]" for r in response['references'] if r.get('start') is not None)[:120]
        if ref_str:
            answer = f"{answer.strip()}\n\nReferenced timestamps: {ref_str}"
    usage = _build_usage(question, answer)
    return {"answer": answer, "references": response.get('references', []), "usage": usage}

# --- Agent / multi-turn extensions ---

def _history_path(media_id: str, user_id: str | None) -> Path:
    uid = user_id or 'anon'
    return CACHE_DIR / f"{media_id}_chat_{uid}.json"

def load_history(media_id: str, user_id: str | None) -> List[Dict]:  # small helper
    path = _history_path(media_id, user_id)
    if path.exists():
        try:
            return json.load(open(path, 'r', encoding='utf-8'))
        except Exception:
            return []
    return []

def save_history(media_id: str, user_id: str | None, history: List[Dict]):
    path = _history_path(media_id, user_id)
    try:
        json.dump(history[-40:], open(path, 'w', encoding='utf-8'), indent=2)  # keep last 40 turns
    except Exception:
        pass

async def chat_agent(media_id: str, question: str, user: dict):
    """Agent-style chat: keeps short history and retrieval-augments each answer.

    Strategy:
      1. Load transcript segments
      2. Retrieve top-N relevant segments by keyword overlap
      3. Load previous conversation turns and include the last few in prompt
      4. Ask model to answer grounded ONLY in provided segments; if unknown say you don't know
    """
    trans = await maybe_handle_translation(media_id, question)
    if trans:
        return trans
    data = load_transcript(media_id)
    if not data:
        return {"answer": "Transcript not found.", "references": [], "history": []}
    user_id = user.get('id') if isinstance(user, dict) else 'anon'
    history = load_history(media_id, user_id)
    # Basic sanitization of history strings
    trimmed_history = history[-8:]  # last 8 messages
    # Build retrieval context
    segments = data.get('segments', [])
    terms = [t for t in question.lower().split() if len(t) > 2]
    scored = []
    for seg in segments:
        text = seg.get('text','')
        lt = text.lower()
        score = sum(lt.count(t) for t in terms)
        if score:
            scored.append((score, seg))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:10]] or segments[:5]
    context = "\n".join([f"[{s.get('start'):.1f}-{s.get('end'):.1f}] {s.get('text')}" for s in top])[:6000]
    # Compose conversation excerpt
    convo_lines = []
    for m in trimmed_history:
        role = m.get('role')
        if role in ('user','assistant'):
            convo_lines.append(f"{role.title()}: {m.get('content','')[:500]}")
    convo_block = "\n".join(convo_lines)
    prompt = (
        "You are a helpful expert assistant answering questions about a media transcript.\n"
        "Use ONLY the provided transcript snippets as factual source. If the answer isn't in them, say you don't know.\n"
        "Cite timestamps in square brackets where relevant. Be concise.\n"\
        f"Transcript Snippets:\n{context}\n\nConversation So Far (recent turns):\n{convo_block}\n\nUser Question: {question}\nAnswer:"
    )
    raw = await call_gemini(prompt)
    refs = [{"start": s.get('start'), "end": s.get('end'), "text": s.get('text','')} for s in top[:6]]
    # Update history
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": raw})
    save_history(media_id, user_id, history)
    usage = _build_usage(question, raw, extra_context=len(context)+len(convo_block))
    return {"answer": raw, "references": refs, "history": history[-20:], "usage": usage}

async def chat_gpt(media_id: str, question: str, user: dict):
    """GPT-like general chat (not strictly grounded) using accumulated history.

    It still lightly uses transcript (short summary) for context but allows broader reasoning.
    """
    trans = await maybe_handle_translation(media_id, question)
    if trans:
        return trans
    data = load_transcript(media_id)
    transcript_summary = ''
    if data:
        segs = data.get('segments', [])
        if segs:
            joined = ' '.join(s.get('text','') for s in segs[:150])
            transcript_summary = joined[:4000]
    user_id = user.get('id') if isinstance(user, dict) else 'anon'
    history = load_history(media_id, user_id)
    # Build conversation (truncate to last ~3000 chars)
    convo = []
    for m in history[-30:]:
        role = m.get('role'); content = m.get('content','')
        if role in ('user','assistant'):
            convo.append(f"{role}: {content}")
    convo_text = '\n'.join(convo)
    base_prompt = (
        "You are a helpful, detailed AI assistant (like ChatGPT). Answer the user.\n"
        "If a transcript context is provided, prefer facts from it; otherwise use general knowledge.\n"
        "Keep answers concise but informative.\n"
    )
    prompt = f"{base_prompt}\nTranscript Context (optional):\n{transcript_summary}\n\nConversation So Far:\n{convo_text}\n\nUser: {question}\nAssistant:"
    raw = await call_gemini(prompt)
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": raw})
    save_history(media_id, user_id, history)
    usage = _build_usage(question, raw, extra_context=len(transcript_summary)+len(convo_text))
    return {"answer": raw, "references": [], "history": history[-30:], "usage": usage}

# ---- Token / usage estimation helpers ----

def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # crude approximation: tokens ~ words * 1.3
    words = len(text.strip().split())
    return int(words * 1.3)

def _build_usage(prompt_q: str, completion: str, extra_context: int = 0) -> Dict:
    prompt_tokens = _estimate_tokens(prompt_q) + int(extra_context/4)
    completion_tokens = _estimate_tokens(completion)
    total = prompt_tokens + completion_tokens
    # cost estimate placeholder (model pricing not embedded)
    cost = round(total / 1_000_000, 6)  # meaningless placeholder; adjust with real pricing
    return {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total, "cost_estimate_usd": cost}

# ---- History management public helpers ----

def clear_history(media_id: str, user_id: str | None):
    p = _history_path(media_id, user_id)
    try:
        if p.exists():
            p.unlink()
            return True
    except Exception:
        return False
    return True

def list_history(media_id: str, user_id: str | None) -> List[Dict]:
    return load_history(media_id, user_id)

async def stream_chunks(answer: str, size: int = 120):
    # simple chunk generator splitting by size boundaries at whitespace
    buf = ''
    for part in answer.split():
        if len(buf) + len(part) + 1 > size and buf:
            yield buf
            buf = part
        else:
            buf = f"{buf} {part}".strip()
    if buf:
        yield buf

import os, json
import numpy as np
from pathlib import Path
from .storage_access import load_transcript

try:
    import faiss  # type: ignore
except ImportError:  # Graceful degrade when faiss not available (e.g., Windows pip)
    faiss = None  # type: ignore

# Sentence-transformers real model (lazy load)
_st_model = None
_MODEL_NAME = os.getenv('EMBED_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')

def _get_model():
    global _st_model
    if _st_model is None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            _st_model = SentenceTransformer(_MODEL_NAME)
        except Exception:
            _st_model = None
    return _st_model

EMB_DIR = Path('storage/embeddings')
EMB_DIR.mkdir(parents=True, exist_ok=True)

def _fallback_embed(texts):
    # Deterministic hash-based embedding fallback.
    vecs = []
    for t in texts:
        rng = np.random.default_rng(abs(hash(t)) % (2**32))
        vec = rng.normal(size=384).astype('float32')
        norm = np.linalg.norm(vec) + 1e-9
        vecs.append(vec / norm)
    return np.vstack(vecs)

def _embed(texts):
    model = _get_model()
    if model is None:
        return _fallback_embed(texts)
    try:
        emb = model.encode(texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
        if emb.dtype != np.float32:
            emb = emb.astype('float32')
        return emb
    except Exception:
        return _fallback_embed(texts)

def build_or_load_index(media_id: str):
    if faiss is None:
        return None, None
    idx_path = EMB_DIR / f"{media_id}.index"
    meta_path = EMB_DIR / f"{media_id}.json"
    if idx_path.exists() and meta_path.exists():
        index = faiss.read_index(str(idx_path))
        with open(meta_path,'r',encoding='utf-8') as f:
            meta = json.load(f)
        return index, meta
    data = load_transcript(media_id)
    if not data:
        return None, None
    segments = data.get('segments', [])
    texts = [s.get('text','') for s in segments]
    if not texts:
        return None, None
    embeddings = _embed(texts)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, str(idx_path))
    with open(meta_path,'w',encoding='utf-8') as f:
        json.dump({'count': len(texts)}, f)
    return index, {'count': len(texts)}

def search_embeddings(media_id: str, query: str, top_k: int = 5):
    if faiss is None:
        return None  # triggers BM25 fallback upstream
    index, meta = build_or_load_index(media_id)
    if not index:
        return None
    q_vec = _embed([query])
    sims, ids = index.search(q_vec, top_k)
    data = load_transcript(media_id)
    segs = data.get('segments', []) if data else []
    results = []
    for i, score in zip(ids[0], sims[0]):
        if i < 0 or i >= len(segs):
            continue
        seg = segs[i]
        results.append({
            'text': seg.get('text',''),
            'timestamp': seg.get('start'),
            'score': float(score)
        })
    return results
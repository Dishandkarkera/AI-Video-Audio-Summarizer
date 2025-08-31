from rank_bm25 import BM25Okapi
from typing import List, Dict
from .storage_access import load_transcript
from .embedding_service import search_embeddings

async def search(media_id: str, query: str):
    data = load_transcript(media_id)
    if not data:
        return []
    segments = data.get('segments', [])
    # Try embedding search first
    emb_results = search_embeddings(media_id, query)
    if emb_results:
        return emb_results
    # Fallback BM25
    docs = [seg.get('text','') for seg in segments]
    tokenized = [doc.split() for doc in docs if doc]
    if not tokenized:
        return []
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.split())
    ranked = sorted(zip(segments, scores), key=lambda x: x[1], reverse=True)[:5]
    return [{
        'text': seg.get('text',''),
        'timestamp': seg.get('start'),
        'score': float(score)
    } for seg, score in ranked]

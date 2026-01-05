# api/retrieval.py
"""
Vector retrieval (pgvector) with an authority constraint and a confidence guardrail.

Key behaviors:
- Always filters by document version (authority boundary).
- Returns only "strong" matches via MIN_SCORE (refuse if weak/unrelated).
- Enforces hard TOP_K (context window protection).
"""

import os
from typing import Any, Dict, List

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "")
TOP_K = int(os.getenv("TOP_K", "5"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.35"))

# Candidate pool lets you fetch more than TOP_K, then threshold-filter and trim.
# This helps avoid "TOP_K all weak" cases and makes MIN_SCORE meaningful.
CANDIDATE_POOL = int(os.getenv("CANDIDATE_POOL", str(max(25, TOP_K * 10))))

# pgvector distance: <=> is cosine distance when using vector_cosine_ops
# We convert to similarity score: score = 1 - distance  (range roughly [-inf, 1], usually 0..1)
SQL = """
SELECT
  c.id,
  c.text,
  c.section,
  c.page_start,
  c.page_end,
  d.source,
  d.version,
  1 - (c.embedding <=> %s) AS score
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE d.version = %s
  AND c.embedding IS NOT NULL
ORDER BY c.embedding <=> %s
LIMIT %s;
"""

def retrieve(query_embedding: List[float], version: str = "v1") -> List[Dict[str, Any]]:
    """
    Returns a list of chunk dicts ordered by similarity (best first),
    filtered by MIN_SCORE, capped at TOP_K.

    If nothing meets MIN_SCORE, returns [] (caller should refuse).
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    # Pull a larger candidate set so filtering doesn't starve TOP_K
    limit = max(TOP_K, CANDIDATE_POOL)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL, (query_embedding, version, query_embedding, limit))
            rows = cur.fetchall()

    results: List[Dict[str, Any]] = [
        {
            "id": r[0],
            "text": r[1],
            "section": r[2],
            "page_start": r[3],
            "page_end": r[4],
            "source": r[5],
            "version": r[6],
            "score": float(r[7]),
        }
        for r in rows
    ]

    # Confidence guardrail: keep only strong matches
    strong = [r for r in results if r["score"] >= MIN_SCORE]

    # Hard cap (context protection)
    return strong[:TOP_K]


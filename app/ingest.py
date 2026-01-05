import os
import re
import hashlib
import requests
import psycopg
from pypdf import PdfReader

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag@db:5432/rag")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Hard limits (keep ingestion safe)
MAX_PAGE_CHARS = int(os.getenv("MAX_PAGE_CHARS", "20000"))     # guard against garbage pages
CHUNK_CHARS = int(os.getenv("CHUNK_CHARS", "1800"))            # simple char-based chunking
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))         # small overlap for continuity

def normalize_text(t: str) -> str:
    t = t.replace("\x00", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def strip_headers_footers(page_text: str) -> str:
    """
    Minimal heuristic:
    - remove repeated page numbers lines
    - remove obvious header/footer patterns if present
    (Keeps it simple for Day 17)
    """
    lines = [ln.strip() for ln in page_text.splitlines()]
    cleaned = []
    for ln in lines:
        if re.fullmatch(r"\d+", ln):  # just a page number
            continue
        if len(ln) <= 2:
            continue
        cleaned.append(ln)
    return "\n".join(cleaned).strip()

def chunk_text(text: str):
    # Simple sliding window over characters (tokenizer-free, offline-safe)
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + CHUNK_CHARS, n)
        chunk = text[i:j].strip()
        if chunk:
            chunks.append(chunk)
        if j == n:
            break
        i = max(0, j - CHUNK_OVERLAP)
    return chunks

def embed(text: str):
    # Ollama embeddings endpoint
    payload = {"model": EMBED_MODEL, "prompt": text}
    r = requests.post(f"{OLLAMA_BASE_URL}/api/embeddings", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["embedding"]

def main(pdf_path: str, source: str, version: str = "v1"):
    reader = PdfReader(pdf_path)

    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        raw = normalize_text(raw)
        raw = strip_headers_footers(raw)

        # Guardrail: drop suspicious pages (often scanned garbage)
        if len(raw) > MAX_PAGE_CHARS:
            print(f"[WARN] Page {idx} too large ({len(raw)} chars). Dropping to avoid context pollution.")
            raw = raw[:MAX_PAGE_CHARS]

        if raw:
            pages.append((idx, raw))

    if not pages:
        raise SystemExit("No extractable text found. (OCR is off by design.)")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Create document record
            cur.execute(
                "INSERT INTO documents (source, version) VALUES (%s, %s) RETURNING id",
                (source, version),
            )
            doc_id = cur.fetchone()[0]

            chunk_idx = 0
            for page_num, text in pages:
                # Optional: set section later; for now keep simple
                section = f"Page {page_num}"

                for ch in chunk_text(text):
                    text_hash = hashlib.sha256(ch.encode("utf-8")).hexdigest()

                    # Dedup guard: skip if already seen (same doc or reingest)
                    cur.execute("SELECT 1 FROM chunks WHERE text_hash=%s LIMIT 1", (text_hash,))
                    if cur.fetchone():
                        continue

                    vec = embed(ch)

                    cur.execute(
                        """
                        INSERT INTO chunks
                          (document_id, chunk_index, page_start, page_end, section, text, text_hash, embedding)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (doc_id, chunk_idx, page_num, page_num, section, ch, text_hash, vec),
                    )
                    chunk_idx += 1

            conn.commit()

    print(f"[OK] Ingested doc_id={doc_id} chunks={chunk_idx} pages={len(pages)} embed_model={EMBED_MODEL}")

if __name__ == "__main__":
    pdf_path = os.getenv("PDF_PATH", "/data/manual.pdf")
    source = os.getenv("DOC_SOURCE", "manual.pdf")
    version = os.getenv("DOC_VERSION", "v1")
    main(pdf_path, source, version)

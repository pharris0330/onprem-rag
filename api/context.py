import re
import os

MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))

INSTRUCTION_PATTERNS = [
    r"ignore previous",
    r"system:",
    r"assistant:",
    r"you are an ai",
]

def strip_instruction_text(text: str) -> str:
    lowered = text.lower()
    for pat in INSTRUCTION_PATTERNS:
        if pat in lowered:
            return ""
    return text

def assemble_context(chunks):
    if not chunks:
        raise ValueError("EMPTY_RETRIEVAL")

    context_parts = []
    total_chars = 0
    citations = []

    for c in chunks:
        clean = strip_instruction_text(c["text"])
        if not clean:
            continue

        header = f"[{c['source']} | {c['section']} | p{c['page_start']}]"
        block = f"{header}\n{clean}\n"

        if total_chars + len(block) > MAX_CONTEXT_CHARS:
            break

        context_parts.append(block)
        total_chars += len(block)
        citations.append(header)

    if not context_parts:
        raise ValueError("CONTEXT_BLOCKED")

    return "\n".join(context_parts), citations

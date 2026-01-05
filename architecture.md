
# Architecture — On-Prem Secure RAG Lab

This document describes the **system architecture, trust boundaries, and failure zones** for the on-prem, context-controlled RAG lab.

The goal is not model cleverness, but **control, safety, and recoverability**.

---

## 1. High-Level System Architecture

This diagram shows **what exists** in the system and **why**.

```

┌───────────────┐
│ User / Client │
└───────┬───────┘
│
v
┌────────────────────┐
│ API / Gateway      │
│ - Auth             │
│ - Rate limits      │
│ - Size caps        │
│ - Timeouts         │
│ - Request IDs      │
└───────┬────────────┘
│
v
┌────────────────────┐
│ Ingestion Pipeline │
│ (PDF → clean text) │
└───────┬────────────┘
│
v
┌────────────────────┐
│ Chunking + Metadata│
│ - Sections         │
│ - Pages            │
│ - Version          │
└───────┬────────────┘
│
v
┌────────────────────┐
│ Embeddings (local) │
└───────┬────────────┘
│
v
┌──────────────────────────────┐
│ PostgreSQL + pgvector        │
│ - Vector index               │
│ - Relational metadata        │
└───────┬──────────────────────┘
│
v
┌────────────────────┐
│ Hybrid Retrieval   │
│ - Vector similarity│
│ - SQL constraints  │
│ - Top-K            │
└───────┬────────────┘
│
v
┌────────────────────┐
│ Context Assembly   │
│ - Ordering         │
│ - Framing          │
│ - Size caps        │
│ - Instruction strip│
└───────┬────────────┘
│
v
┌────────────────────┐
│ Local LLM (Ollama) │
└───────┬────────────┘
│
v
┌────────────────────┐
│ Guardrails         │
│ - Refusal logic    │
│ - Citation checks  │
└───────┬────────────┘
│
v
┌────────────────────┐
│ Answer + Citations │
└────────────────────┘

```

**Key idea:**  
> The model is *downstream*. Most correctness and safety happens **before** it.

---

## 2. Trust Boundaries & Security Model

This is the **most important diagram** in the system.

```

UNTRUSTED INPUT
────────────────────────────────────────────
• User input
• PDF documents
• OCR output
• Retrieved chunks
────────────────────────────────────────────
|
v
┌────────────────────┐
│ Context Assembly   │
│ - Filter           │
│ - Order            │
│ - Cap size         │
│ - Strip instructions
└─────────┬──────────┘
|
══════════════════ TRUST BOUNDARY ══════════════════
|
v
┌────────────────────┐
│ Context Window     │
│ (Trusted evidence)│
└─────────┬──────────┘
|
v
┌────────────────────┐
│ LLM Reasoning      │
└────────────────────┘

```

### Security Principles
- **Documents are untrusted**
- **Retrieved text is untrusted**
- **Only assembled context is trusted**
- Prompt injection fails *before* the boundary

> **Context control is a security feature.**

---

## 3. Failure Zones & Guardrails (Operations View)

This diagram shows **where systems fail** and **where failures are stopped**.

```

┌────────────────────┐
│ API / Gateway      │
│                    │
│ Failures:          │
│ - No auth          │
│ - No limits        │
│ - Hanging requests │
│                    │
│ Controls:          │
│ - Rate limits      │
│ - Timeouts         │
│ - Logging          │
└─────────┬──────────┘
|
v
┌────────────────────┐
│ Retrieval           │
│                    │
│ Failures:          │
│ - Empty results    │
│ - Weak similarity  │
│ - Conflicting docs │
│                    │
│ Guardrail:         │
│ - Pre-gen refusal  │
└─────────┬──────────┘
|
v
┌────────────────────┐
│ Context Assembly   │
│                    │
│ Failures:          │
│ - Overflow         │
│ - Bad ordering     │
│ - Injection text   │
│                    │
│ Guardrail:         │
│ - Size caps        │
│ - Strip instructions
│ - Refuse safely    │
└─────────┬──────────┘
|
v
┌────────────────────┐
│ Model               │
│                    │
│ Risk:              │
│ - Hallucination    │
│                    │
│ Guardrail:         │
│ - Post-gen checks  │
│ - Citation enforce │
└────────────────────┘

```

**Operational rule:**
> If evidence is weak or unsafe, **refuse** — do not guess.

---

## 4. Observability & Recovery

Every request must be explainable **after the fact**.

Minimum logs:
- Request ID
- Retrieval count + scores
- Context size / hash
- Guardrail decisions
- Latency / timeout events

```

If you can’t see what the model saw,
you can’t debug or trust the system.

```

---

## 5. Architectural Takeaways

- Models do not read documents — they reason over **selected context**
- Context assembly is the **highest-risk component**
- Gateways enforce **policy, not intelligence**
- Guardrails are **required**, not optional
- Safe refusal is correct behavior

---

## One-Sentence Summary

> **The most important architectural decision in RAG is where you draw the trust boundary.**
```

---


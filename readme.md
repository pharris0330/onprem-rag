# On-Prem Secure RAG Lab (Context-Controlled)

This lab demonstrates a **production-grade, on-prem Retrieval-Augmented Generation (RAG)** system designed to safely answer questions from **PDF manuals** under **strict constraints**.

The focus is **not model cleverness**, but **system correctness**:
- context control
- security boundaries
- safe refusal
- observability
- offline operation

---

## 🎯 Goals

By the end of this lab, the system:
- Runs **fully offline**
- Ingests a real PDF manual
- Retrieves evidence using **pgvector + SQL**
- Assembles a **bounded, trusted context**
- Refuses safely when evidence is weak or unsafe
- Logs enough information to debug incidents

This mirrors real-world on-prem / air-gapped deployments.

---

## 🧠 Core Design Principles

- **Models reason over context, not documents**
- **Context is a trust boundary**
- **Gateways enforce policy, not intelligence**
- **Safe refusal beats fluent guessing**
- **Observability beats optimism**

---

## 🧱 Architecture Overview

```

User
↓
API / Gateway
(auth, size limits, timeouts, logs)
↓
Ingestion (PDF → clean text)
↓
Chunking + Metadata
↓
Embeddings (local)
↓
Hybrid Retrieval (Vector + SQL)
↓
Context Assembly (guarded)
↓
Local LLM (Ollama)
↓
Guardrails
↓
Answer + Citations

```

---

## 🧩 Components

### API / Gateway (FastAPI)
- Enforces authentication
- Enforces request size limits
- Enforces timeouts
- Issues request IDs
- Logs all activity

The gateway **never interprets content**.

---

### Ingestion
- Parses PDF text only (OCR is OFF by default)
- Strips headers / footers
- Deduplicates text via hash
- Applies page-size guardrails

**Purpose:** prevent garbage text and token explosion.

---

### Chunking + Metadata
- Fixed-size hierarchical chunks
- Metadata includes:
  - section
  - page
  - source
  - version

**Purpose:** preserve meaning and ordering.

---

### Embeddings (Ollama)
- Uses a local embedding model
- Embeddings are **selectors**, not truth
- Stored in PostgreSQL via pgvector

---

### Hybrid Retrieval
Order is enforced:

```

Vector similarity
→ SQL authority filters (version)
→ Confidence threshold (MIN_SCORE)
→ Hard TOP_K

````

**Purpose:** relevance + precision.

---

### Context Assembly (Critical Boundary)
- Orders chunks by document structure
- Adds framing headers
- Strips instruction-like text
- Enforces context size limits

Everything entering context is treated as **trusted**.

---

### Guardrails
**Pre-generation**
- Refuse on empty retrieval
- Refuse on weak similarity
- Refuse on context overflow (optional strict mode)

**Post-generation**
- Require citations
- Refuse ungrounded answers

---

### Observability
At minimum, the system logs:
- retrieval count + scores
- context size
- refusal reason codes
- latency

If you can’t see what the model saw, you can’t trust the system.

---

## ⚙️ Tech Stack

- Python 3.11
- FastAPI
- PostgreSQL + pgvector
- Ollama (local LLM + embeddings)
- Docker Compose

---

## 🚀 Running the Lab

### 1. Start services
```bash
docker compose up -d --build
````

### 2. Pull models inside Ollama container

```bash
docker exec -it onprem-rag-ollama-1 ollama pull llama3.1:8b
docker exec -it onprem-rag-ollama-1 ollama pull nomic-embed-text
```

---

## 📄 Ingest a Manual

Place a PDF in:

```
/data/manual.pdf
```

Run ingestion:

```bash
docker exec -it onprem-rag-api-1 python ingest.py
```

Verify:

```bash
SELECT count(*) FROM documents;
SELECT count(*) FROM chunks;
```

---

## 🔎 Query the System

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-local-key" \
  -d '{"question":"What is the purpose of this manual?"}'
```

Responses include:

* answer
* citations
* request_id
* latency

---

## 🧪 Safety & Failure Tests

These should **refuse**, not guess:

1. Ask an unrelated question
2. Delete all chunks and ask
3. Inflate TOP_K to overflow context
4. Inject instruction text into a document chunk

Each refusal must be visible in logs.

---

## 📊 Evaluation

A minimal evaluation harness is included:

* golden question set
* pass/fail on answer vs refusal

Run:

```bash
docker exec -it onprem-rag-api-1 python eval_run.py
```

---

## ✅ Current Status

Implemented:

* Offline RAG pipeline
* Context control
* Hybrid retrieval
* Guardrails
* Evaluation harness
* Operational logging

Not yet implemented:

* Rerankers
* Graph retrieval
* Fine-tuning
* Autoscaling
* UI

These are intentionally out of scope.

---

## 🧠 Key Takeaway

> **Reliable AI systems are engineered, not prompted.**

This lab proves the ability to design, build, and operate a **safe, production-ready on-prem RAG system**.

---

## 📌 Next Steps (Optional)

* Harden logs for audit
* Add rerankers
* Introduce graph-enhanced retrieval
* Stress-test under load
* Add incident runbooks

```

---


```

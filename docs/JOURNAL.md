# 📝 Build journal — Study-Group RAG Tutor

The plain-English story of how this was built, phase by phase. It was built in
small, tested slices — one coherent change per commit, never starting the next
slice until the current one was green.

## The idea

Most "chat with your PDF" demos are single-user and ungrounded. I wanted
something a **whole class** could share: upload the course materials once, then
let everyone ask questions and practice — with answers that **cite the source**
and admit when they don't know, plus quizzes generated from the same material.

## Phase 0 — Foundation

Scaffolded the backend, pinned every dependency, and stood up the canonical CI
pipeline early (secret scan, dependency CVEs, CodeQL, lint, types, security
lint, tests) so quality was enforced from commit one rather than bolted on.

## Phase 1 — The RAG core

Built the engine as a pure, unit-tested library before any web framework:
- **Chunking** — split extracted text into overlapping character windows.
- **Embeddings** — `fastembed` with `all-MiniLM-L6-v2`. This was a deliberate
  choice for a memory-constrained machine: it runs the model as ONNX on CPU with
  no PyTorch, so it's light and free.
- **Vector store** — originally ChromaDB, but a critical pre-auth RCE advisory
  made it untenable, so I swapped to **sqlite-vec**. That turned into a feature:
  the relational data and the vectors now live in **one SQLite file**, written
  through one connection. Vectors are partitioned by course so retrieval never
  crosses class boundaries.
- **Grounded answers** — the LLM (Groq `llama-3.3-70b-versatile`) is told to
  answer only from the retrieved context and to cite sources; if retrieval finds
  nothing, it short-circuits to an honest "I don't know" without calling the LLM.

## Phase 2–3 — Backend API & multi-user spaces

Wrapped the core in FastAPI using an app-factory (no module-level app, so
importing has no side effects and tests can inject doubles). Added course
spaces, idempotent student join, PDF upload + ingest, and the cited `/ask`
endpoint. Retrieval is scoped per course throughout.

## Phase 4 — Quiz tutor

Added quiz generation using the model's **JSON mode** for structured output,
strictly validated into typed questions (a malformed model response raises
rather than being passed off as a quiz). For scoring I chose **server-side
persistence**: the generated quiz — including the answer key — is stored, and
`/quiz` returns the questions with the key withheld. Submitting answers scores
against the stored key and reveals per-question explanations only afterwards.

## Phase 5 — The frontend

Decision point: the UI had to be portfolio-grade, but on a RAM-constrained
machine. I picked **Vite + React + shadcn/ui** over Next.js (lighter in dev, no
SSR server) and over Streamlit (which can't hit the bar). Built a real design
token system with light/dark themes, then shipped the screens slice by slice —
join, upload, ask, quiz, progress — each with loading/empty/error states,
accessibility checks (automated axe), and tests. The dev server proxies `/api`
to the backend so there's no CORS dance during development.

A couple of honest bumps along the way, fixed rather than papered over: a
heading-order accessibility violation (cards were forcing an `<h3>` after the
page `<h1>`), and two test gotchas around how the file input's `accept` filter
and a page subtitle interacted with queries.

## Phase 6 — Real data & proof

No fake data: I loaded two real chapters from OpenStax *Concepts of Biology*
(CC BY 4.0) — Cell Structure and Function, and Photosynthesis — into a `BIO101`
course (185 indexed chunks). Then I ran the whole stack for real and verified a
grounded answer and a generated quiz end-to-end, and captured six screenshots
from the **production build** using a Playwright script that drives the actual
app (so it doubles as a live smoke test).

## Phase 7 — Documentation & diagrams

Wrote the architecture diagrams (derived from the code, not invented), the
canonical README, this journal, and the technical report — and enforced the
100% backend coverage in CI so the claim is real.

## What stayed true throughout

- **No fake data.** Every screenshot and every demo answer comes from a real run
  on real, open-licensed material.
- **Tests with every feature.** The backend sits at 100% coverage (now enforced);
  the frontend has render, interaction, and accessibility tests.
- **Small, honest commits.** The history reads like the product was built
  feature by feature, because it was.

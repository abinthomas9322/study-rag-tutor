# 🔬 Technical report — Study-Group RAG Tutor

A design deep-dive into how the system works and why it's built this way. All
numbers here come from the real code and a real run; the diagrams referenced
live in [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Overview

The product is a course-scoped retrieval-augmented generation (RAG) assistant.
A class shares one *course space*; uploaded PDFs are indexed into a per-course
vector store; questions are answered strictly from retrieved passages with
citations, and quizzes are generated from the same content and scored
server-side.

The system has three parts:

- **RAG core** (`backend/rag`) — a pure, framework-free library: PDF text
  extraction, chunking, embeddings, the vector store, and the answer/quiz
  generators.
- **API layer** (`backend/app`) — FastAPI over the core, plus the relational
  data access and HTTP schemas.
- **Frontend** (`frontend/src`) — a Vite + React SPA.

## 2. Ingestion pipeline

`services.ingest_pdf` composes the core:

1. **Extract** — `rag/pdf.py` pulls text from the PDF (pypdf). Image-only PDFs
   yield no text and are rejected with a clear error.
2. **Chunk** — `rag/chunking.py` splits the text into overlapping character
   windows: **800 characters** with **120 characters of overlap** (defaults in
   `rag/config.py`). Overlap preserves context across chunk boundaries.
3. **Embed** — `rag/embeddings.py` wraps `fastembed` with
   `sentence-transformers/all-MiniLM-L6-v2`, producing **384-dimensional**
   vectors. The model is ONNX/CPU (no PyTorch) and loaded lazily on first use.
4. **Store** — `rag/store.py` writes chunk text to a `chunks` table and the
   vector to a `vec_chunks` `sqlite-vec` virtual table sharing the same
   `chunk_id`. The document row is written **last**, so a failure mid-embedding
   never leaves a document recorded without its chunks.

On the demo course (two OpenStax chapters) this produces **185 chunks**
(133 + 52).

## 3. Vector store & course scoping

The store is **sqlite-vec** — chosen after ChromaDB was dropped over a critical
pre-auth RCE advisory with no fixed release. The win: relational rows and
vectors live in **one SQLite file**, written through a single shared connection
(`rag/store.connect` loads the extension once; `app/db.Database` reuses it).

`vec_chunks` uses a **partition key on `course_id`**, so a similarity search only
ever ranks chunks within the queried course — one class can never retrieve
another's material. Retrieval returns the top **k = 4** nearest chunks by
distance.

## 4. Grounded answering & anti-hallucination

`services.answer_question` embeds the question, retrieves the course-scoped
top-k, and hands them to `rag/answer.AnswerGenerator`:

- The system prompt instructs the model to answer **only** from the supplied
  context and to cite `[Source N]`.
- If retrieval returns nothing, the generator **short-circuits** to a fixed
  "I don't know" message and never calls the LLM — no tokens spent, no
  hallucination possible on empty context.
- Generation uses Groq's OpenAI-compatible API with
  `llama-3.3-70b-versatile` at **temperature 0.1** for determinism.

The HTTP response returns the answer plus the source passages, which the
frontend maps back to document filenames for display.

## 5. Quiz generation & scoring

`rag/quiz.py` generates quizzes from the same retrieval (focused on a topic, or
an even **sample** across the course when no topic is given):

- The model is called in **JSON mode** (`response_format={"type":"json_object"}`)
  at temperature 0.3 and asked for `{questions:[{stem, options[4], correct_index,
  explanation}]}`.
- `parse_quiz` **strictly validates** each question (exactly four non-empty
  string options, an in-range integer `correct_index` — `bool` rejected); a
  malformed response raises rather than yielding a broken quiz (surfaced as
  HTTP 502).
- **Server-side answer key.** The generated quiz is persisted
  (`quizzes` + `quiz_questions`) and `POST /quiz` returns the questions with the
  key withheld. `score_quiz` is a pure function comparing submitted indices to
  the stored key; `POST .../attempts` stores the attempt and only then returns
  per-question feedback (correct answer + explanation).

## 6. Data model

Eight tables (see the ER diagram). The relational tables
(`courses`, `students`, `documents`, `quizzes`, `quiz_questions`,
`quiz_attempts`) live in `app/db.py`; `chunks` and `vec_chunks` live in
`rag/store.py`. Every relational child **cascade-deletes** from `courses`, so
removing a course cleans up its students, documents, quizzes, and attempts.
Options and submitted answers are stored as JSON and round-tripped to typed
lists.

## 7. API

Eleven endpoints plus `/health` (`app/routes.py`), covering course CRUD, join,
upload/list documents, ask, quiz generation, attempt submission, and a student's
attempt history. Dependencies are injected from `app.state` via `app/deps.py`,
keeping routes thin and testable.

## 8. Frontend

Vite + React + TypeScript with shadcn/ui (Radix) and a CSS-variable design-token
system driving light/dark themes. Routing is `react-router`; server state is
`TanStack Query`; forms use `react-hook-form` + `zod`. The session (joined
course + student) persists in `localStorage`. In development and in the
production preview, `/api` is proxied to the backend, so no CORS configuration is
needed for local use.

## 9. Testing strategy

- **Backend** — unit tests for the core (chunking, embeddings, store, answer,
  quiz, scoring) and integration tests for every endpoint, including error and
  negative paths, parametrized across the input space. External boundaries
  (the LLM, the embedder) are faked; the logic under test runs for real, against
  real in-memory SQLite + sqlite-vec. **Coverage is 100%, enforced in CI**
  (`--cov-fail-under=100`).
- **Frontend** — render, interaction, and **accessibility** tests (Vitest +
  Testing Library + vitest-axe) across all screens and the session store
  (**40 tests**). The boundary (the API client) is mocked; routing, guards,
  validation, and state run for real.

## 10. Security & CI

Every push/PR runs gitleaks (secrets), Trivy (dependency/filesystem CVEs,
failing on CRITICAL/HIGH), CodeQL (Python + JS/TS), and the language quality
jobs (ruff, mypy, bandit, pip-audit, pytest; eslint, prettier, tsc, vitest,
build, npm audit). Versions are pinned via requirements and the npm lockfile;
`npm audit` is clean. Secrets live only in `.env` (git-ignored); only
`.env.example` is committed.

## 11. Known limitations

- **No auth.** Students are identified by a display name within a course; there's
  no password/identity layer. Fine for a trusted study group; not for the open
  internet.
- **CORS** isn't configured on the backend — local use relies on the Vite proxy;
  a real deployment would add CORS (or serve the SPA from the same origin).
- **Chat is stateless per question** — `/ask` doesn't carry conversation history;
  each question is answered independently.
- **No deployment yet** — running is local; hosting is tracked as Phase 9.

## 12. Measured results

- Demo course: 2 documents → **185 indexed chunks**.
- Backend: **100% line coverage** (enforced), 606 measured statements.
- Frontend: **40 tests** passing; production build clean; **0** npm audit
  vulnerabilities.
- Verified live end-to-end: a grounded answer with four cited sources, and a
  generated, scored photosynthesis quiz.

# 🗺️ ROADMAP — Study-Group RAG Tutor

A shared, multi-user RAG study assistant for a class of ~200 students: upload course
materials once, then ask questions (cited, grounded answers) and generate practice
quizzes from the same material.

Each slice is one small, tested commit. We don't start a slice until the previous one
is green. `%` is cumulative progress toward a 10/10 portfolio-grade repo (the §13
Definition-of-Done gate = 100%).

---

## Phase 0 — Foundation
- [x] 0.1 Scaffold project structure ............ 2%  (commit 783d63b)
- [x] 0.2 Pin backend + dev dependencies ........ 4%  (commit c160c82)
- [x] 0.3 ROADMAP + docs skeleton ............... 6%  (commit f295e3f)
- [x] 0.4 Canonical CI/CD pipeline (green) ...... 9%  (commit cace8c9)

## Phase 1 — Core RAG engine (pure, unit-tested)
- [x] 1.1 Config + text chunking ................ 14%  (commit f2941c2)
- [x] 1.2 Embeddings via fastembed .............. 19%  (commit b086f76)
- [x] 1.3 sqlite-vec persistent ingest + retrieve 25%  (commit 7b05d9b)
- [x] 1.4 Grounded answer generation (Groq) ..... 31%  (commit 485f3d0)

## Phase 2 — Backend API (FastAPI + SQLite)
- [x] 2.1 App factory + health + typed config ... 35%  (commit 45d6011)
- [x] 2.2 SQLite models (courses/students/docs) . 39%  (commit e27a6e7)
- [x] 2.3 Upload + ingest endpoint .............. 44%  (commits e505b81, e670157)
- [x] 2.4 Ask endpoint (cited answers) .......... 48%  (commit d11e7db)

## Phase 3 — Multi-user course spaces
- [x] 3.1 Join-a-class + course-scoped docs ..... 53%  (commit b6cc783)

## Phase 4 — Quiz tutor
- [x] 4.1 Quiz generation endpoint .............. 58%  (commit df766e1)
- [x] 4.2 Quiz scoring + per-student storage .... 62%  (commit b74443b)

## Phase 5 — Frontend (world-class UI, §9b · Vite + React + shadcn/ui)
- [x] 5.1 Vite + React + shadcn scaffold + tokens 66%  (commit 85c40b0)
- [x] 5.2 Join-class screen ..................... 69%  (commit 9c5fd81)
- [x] 5.3 Upload-materials screen ............... 73%  (commit 732f079)
- [x] 5.4 Chat Q&A screen (with sources) ........ 78%  (commit 0823c42)
- [x] 5.5 Quiz screen ........................... 82%  (commit 9e1f8a4)
- [ ] 5.6 Progress screen ....................... 85%

## Phase 6 — Real data & proof (§5)
- [ ] 6.1 Load real open-licensed course + e2e .. 89%
- [ ] 6.2 Capture ≥4 real-run screenshots ....... 91%

## Phase 7 — Documentation & diagrams (§7, §8)
- [ ] 7.1 Mermaid diagrams (arch/DFD/seq/ER) .... 94%
- [ ] 7.2 Canonical 21-section README ........... 97%
- [ ] 7.3 JOURNAL + TECHNICAL_REPORT ............ 99%

## Phase 8 — Ship it green (§13)
- [ ] 8.1 Run Definition-of-Done gate + report .. 100%

## Phase 9 — Deploy & push (post-1.0, only on request)
- [ ] 9.1 Create GitHub repo + push
- [ ] 9.2 Deploy free + live demo link

---

## 📍 Current position
- **Progress:** 82% — Phase 5.5 (quiz screen) complete.
- **Next slice:** 5.6 — Progress screen.
- **Stack note:** UI is **Vite + React + shadcn/ui** (chosen over Next.js/Streamlit
  for a portfolio-grade UI that stays light on a RAM-constrained dev machine).
- **Branch:** `main` (local only — not pushed yet).

## 🐞 Known issues
- GitHub remote not created yet — last attempt returned "Repository not found".
  Repo must be created on the owner's account before any push (Phase 9).
- ChromaDB was swapped for sqlite-vec in 0.x to resolve CVE-2026-45829
  (pre-auth RCE, no fixed release available). Vector store is now sqlite-vec.

## ⏭️ Next up after foundation
Phase 1 — port the proven RAG logic from the earlier `rag-document-assistant`
prototype into a clean, persistent, unit-tested core.

---

## ✍️ TODO: my words
_(Abin — your own notes on priorities, scope changes, and what "done" means to you.)_

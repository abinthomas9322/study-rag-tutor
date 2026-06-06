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
- [ ] 1.1 Config + text chunking ................ 14%
- [ ] 1.2 Embeddings via fastembed .............. 19%
- [ ] 1.3 sqlite-vec persistent ingest + retrieve 25%
- [ ] 1.4 Grounded answer generation (Groq) ..... 31%

## Phase 2 — Backend API (FastAPI + SQLite)
- [ ] 2.1 App factory + health + typed config ... 35%
- [ ] 2.2 SQLite models (courses/students/docs) . 39%
- [ ] 2.3 Upload + ingest endpoint .............. 44%
- [ ] 2.4 Ask endpoint (cited answers) .......... 48%

## Phase 3 — Multi-user course spaces
- [ ] 3.1 Join-a-class + course-scoped docs ..... 53%

## Phase 4 — Quiz tutor
- [ ] 4.1 Quiz generation endpoint .............. 58%
- [ ] 4.2 Quiz scoring + per-student storage .... 62%

## Phase 5 — Frontend (world-class UI, §9b)
- [ ] 5.1 Next.js + shadcn scaffold + tokens .... 66%
- [ ] 5.2 Join-class screen ..................... 69%
- [ ] 5.3 Upload-materials screen ............... 73%
- [ ] 5.4 Chat Q&A screen (with sources) ........ 78%
- [ ] 5.5 Quiz screen ........................... 82%
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
- **Progress:** 9% — Phase 0 (Foundation) complete.
- **Next slice:** 1.1 — config + text chunking (start of the core RAG engine).
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

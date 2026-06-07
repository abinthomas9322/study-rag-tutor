# 🏛️ Architecture — Study-Group RAG Tutor

These diagrams are derived directly from the code; every node maps to a real
module, route, or table. They are written in [Mermaid](https://mermaid.js.org/)
so they render natively on GitHub.

- **Backend** — `backend/app` (FastAPI HTTP layer) + `backend/rag` (the pure RAG
  core). One SQLite file holds both the relational data (`app/db.py`) and the
  vectors (`rag/store.py`, via the `sqlite-vec` extension), shared through a
  single connection.
- **Frontend** — `frontend/src`, a Vite + React SPA that calls the backend under
  `/api` (proxied to the FastAPI server in dev and in the production preview).

---

## 1. System architecture

How the components connect. The browser only ever talks to the backend over
`/api`; embeddings run locally (fastembed/ONNX) while only answer/quiz
generation calls out to Groq.

```mermaid
flowchart TB
  subgraph Browser["Browser — React SPA (frontend/src)"]
    UI["Screens: join · upload · ask · quiz · progress<br/>(routes/, react-router)"]
    SESS["SessionProvider<br/>(localStorage)"]
    CLIENT["api/client.ts<br/>(TanStack Query)"]
    UI --> CLIENT
    UI --> SESS
  end

  CLIENT -->|"HTTP /api/*<br/>(Vite dev and preview proxy)"| ROUTES

  subgraph Backend["FastAPI backend (backend/app)"]
    ROUTES["routes.py<br/>11 endpoints + /health"]
    DEPS["deps.py<br/>(app.state services)"]
    SCHEMAS["schemas.py<br/>(Pydantic I/O)"]
    SVC["services.py<br/>(ingest · answer · quiz · attempts)"]
    DBMOD["db.py<br/>(relational access)"]
    ROUTES --> SVC
    ROUTES --> SCHEMAS
    ROUTES -.-> DEPS
    SVC --> DBMOD
  end

  subgraph Core["RAG core (backend/rag)"]
    PDF["pdf.py<br/>(extract text)"]
    CHUNK["chunking.py"]
    EMB["embeddings.py<br/>(fastembed)"]
    STORE["store.py<br/>(VectorStore)"]
    ANS["answer.py<br/>(AnswerGenerator)"]
    QUIZ["quiz.py<br/>(QuizGenerator · score_quiz)"]
  end

  SVC --> PDF & CHUNK & EMB & STORE & ANS & QUIZ

  SQLITE[("SQLite file — tutor.db<br/>one shared connection")]
  DBMOD --> SQLITE
  STORE --> SQLITE

  EMB -->|"all-MiniLM-L6-v2<br/>(ONNX, local, free)"| FASTEMBED["fastembed runtime"]
  ANS -->|"chat completions"| GROQ["Groq API<br/>llama-3.3-70b-versatile"]
  QUIZ -->|"chat completions<br/>(JSON mode)"| GROQ
```

---

## 2. Data-flow diagram (DFD)

Two flows share the same vector store. **Ingestion** turns an uploaded PDF into
indexed chunks; **querying** turns a question into a grounded, cited answer.

```mermaid
flowchart LR
  subgraph Sources
    PDFIN[/"PDF upload"/]
    Q[/"Student question"/]
  end

  subgraph Ingestion["Ingestion — services.ingest_pdf"]
    EX["extract_text<br/>(pdf.py)"]
    CK["chunk_text<br/>(chunking.py)"]
    EMB1["embed chunks<br/>(embeddings.py)"]
    ADD["store.add<br/>(store.py)"]
    PDFIN --> EX --> CK --> EMB1 --> ADD
  end

  subgraph Query["Query — services.answer_question / generate_quiz"]
    EMB2["embed query / topic"]
    SEARCH["store.search (top-k)<br/>or store.sample"]
    GEN["AnswerGenerator / QuizGenerator"]
    Q --> EMB2 --> SEARCH --> GEN
  end

  CHUNKS[("chunks + vec_chunks<br/>(sqlite-vec, per course)")]
  META[("courses · documents · students<br/>quizzes · quiz_attempts")]

  ADD --> CHUNKS
  ADD --> META
  SEARCH -. reads .-> CHUNKS
  GEN -->|context| LLM["Groq LLM"]
  LLM --> OUT[/"Cited answer / scored quiz"/]
```

---

## 3. Sequence — a grounded `/ask` request

The lifecycle of `POST /courses/{id}/ask`. Retrieval is scoped to the course;
if nothing is retrieved the LLM is never called (an honest "I don't know").

```mermaid
sequenceDiagram
  actor S as Student
  participant FE as React SPA
  participant API as FastAPI route (ask)
  participant SVC as services.answer_question
  participant EMB as Embedder (fastembed)
  participant VS as VectorStore (sqlite-vec)
  participant GEN as AnswerGenerator
  participant LLM as Groq API

  S->>FE: type question
  FE->>API: POST /courses/BIO101/ask {question}
  API->>SVC: answer_question(question, course_id)
  SVC->>EMB: embed_query(question)
  EMB-->>SVC: query vector
  SVC->>VS: search(course_id, vector, k)
  VS-->>SVC: top-k SearchHits (scoped)
  alt no hits
    GEN-->>SVC: "I don't know" (no LLM call)
  else hits found
    SVC->>GEN: generate(question, hits)
    GEN->>LLM: chat.completions (context + question)
    LLM-->>GEN: grounded answer
  end
  SVC-->>API: Answer(text, sources)
  API-->>FE: {answer, sources[]}
  FE-->>S: answer + citations
```

---

## 4. Entity-relationship diagram (ER)

The SQLite schema. `courses`/`students`/`documents`/`quizzes`/`quiz_questions`/
`quiz_attempts` live in `app/db.py`; `chunks` and the `vec_chunks` vector table
live in `rag/store.py`. All relational children cascade-delete from `courses`.

```mermaid
erDiagram
  courses ||--o{ students : enrolls
  courses ||--o{ documents : has
  courses ||--o{ quizzes : has
  courses ||--o{ chunks : scopes
  documents ||--o{ chunks : "split into"
  chunks ||--|| vec_chunks : "embedding for"
  quizzes ||--o{ quiz_questions : contains
  quizzes ||--o{ quiz_attempts : "taken as"
  students ||--o{ quiz_attempts : submits

  courses {
    text id PK
    text name
    text created_at
  }
  students {
    int id PK
    text course_id FK
    text display_name
    text joined_at
  }
  documents {
    text id PK
    text course_id FK
    text filename
    int num_chunks
    text uploaded_at
  }
  chunks {
    int chunk_id PK
    text course_id
    text document_id
    text text
  }
  vec_chunks {
    int chunk_id PK
    text course_id "partition key"
    float embedding "float[384]"
  }
  quizzes {
    text id PK
    text course_id FK
    text topic
    text created_at
  }
  quiz_questions {
    int id PK
    text quiz_id FK
    int position
    text stem
    text options_json
    int correct_index
    text explanation
  }
  quiz_attempts {
    int id PK
    text quiz_id FK
    int student_id FK
    int score
    int total
    text answers_json
    text submitted_at
  }
```

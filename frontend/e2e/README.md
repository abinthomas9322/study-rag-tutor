# End-to-end tests

Playwright tests that drive the **real application** — the built SPA plus a
live FastAPI backend — through the whole product.

These are **local-only** and deliberately not in CI. The happy-path spec calls
the real Groq LLM, so it needs an API key, network access, and ~30–60s to run.
CI keeps covering the units (Vitest render/interaction/a11y tests + the backend
suite at 100% coverage); this suite is the manual full-stack check.

## What's covered

| Spec                        | Checks                                                                                                                                                                                                                                          |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `journey.spec.ts`           | join the seeded BIO101 class → materials list shows the real ingested chapters → ask a question and get a grounded answer with a citations block → generate a quiz, answer it, submit, see a score → the attempt appears on the progress screen |
| `guards-and-errors.spec.ts` | every guarded route bounces an unauthenticated visitor back to join · unknown class code shows a friendly message · empty join form fails client-side validation · the upload screen rejects a non-PDF file                                     |

## Running them

One-time: install the browser binary (not committed, like the screenshot
script's Playwright install):

```bash
cd frontend
npx playwright install chromium
```

Then, from `backend/`, start the API with a real key and the seeded course:

```bash
cp ../.env.example .env          # add your GROQ_API_KEY
python -m seed.seed_demo
uvicorn app.main:create_app --factory --port 8000
```

And from `frontend/`:

```bash
npm run test:e2e                 # builds, serves the preview, runs the suite
```

Playwright starts the `vite preview` server itself. `e2e/global-setup.ts`
checks the backend is up and seeded first, and prints how to start it if not.

## Notes

- One worker: the tests share the backend's SQLite file, and the dev machine
  is memory-constrained.
- Each full run writes one real quiz + attempt into the local `tutor.db`
  (git-ignored, rebuilt any time with `python -m seed.seed_demo`).
- `E2E_BASE_URL` / `E2E_BACKEND_URL` override the default localhost ports.

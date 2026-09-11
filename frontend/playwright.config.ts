import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests for the Study-Group RAG Tutor.
 *
 * These run against the **real stack** — the built SPA served by `vite preview`
 * and a live FastAPI backend (with a real Groq key and the seeded BIO101
 * course). They are deliberately **local-only** and are not part of CI: the
 * happy path calls the real LLM, so it needs a key and network and takes
 * ~30-60s. See `e2e/README.md` for how to run them.
 *
 * Playwright starts the preview server itself; the backend must already be
 * running on :8000 (global setup checks this and fails with instructions).
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  // The happy-path spec drives the real LLM; give it room and one retry.
  timeout: 120_000,
  expect: { timeout: 15_000 },
  retries: 1,
  // One worker: the tests share one backend and one SQLite file, and the
  // dev machine is memory-constrained.
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:4173",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run build && npm run preview -- --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});

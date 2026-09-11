import { request } from "@playwright/test";

/**
 * Fail fast, with instructions, if the backend the E2E tests need isn't up.
 *
 * The preview server proxies /api to :8000, but Playwright only manages the
 * preview server — the FastAPI backend (with a real GROQ_API_KEY and the seeded
 * BIO101 course) has to be started separately.
 */
async function globalSetup() {
  const backend = process.env.E2E_BACKEND_URL ?? "http://localhost:8000";
  const ctx = await request.newContext();
  try {
    const res = await ctx.get(`${backend}/health`, { timeout: 5_000 });
    const body = (await res.json()) as { demo_seeded?: boolean };
    if (!res.ok()) throw new Error(`health returned ${res.status()}`);
    if (!body.demo_seeded) {
      throw new Error(
        "backend is up but the BIO101 demo course isn't seeded — run " +
          "`python -m seed.seed_demo` in backend/ first",
      );
    }
  } catch (err) {
    throw new Error(
      `E2E backend not reachable at ${backend}. Start it first:\n` +
        "  cd backend && uvicorn app.main:create_app --factory --port 8000\n" +
        `(original error: ${(err as Error).message})`,
    );
  } finally {
    await ctx.dispose();
  }
}

export default globalSetup;

/**
 * Capture real-run screenshots of the production build for the README.
 *
 * Prerequisites (all from a real run — no mocking):
 *   1. Backend running on :8000 with a valid GROQ_API_KEY and the seeded
 *      BIO101 course (python -m seed.seed_demo).
 *   2. Frontend production build served by `vite preview` on :4173, which
 *      proxies /api to the backend (see vite.config.ts).
 *
 * Playwright is intentionally NOT a committed dependency (it isn't needed for
 * the build, tests, or CI). Install it ad-hoc just to regenerate screenshots:
 *
 *   npm i --no-save playwright && npx playwright install chromium
 *   node scripts/screenshots.mjs
 *
 * This drives the actual app through join -> upload -> ask -> quiz -> progress,
 * so it also serves as an end-to-end smoke test of the live stack.
 */
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { mkdir } from "node:fs/promises";

import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "../../docs/screenshots");
const BASE = process.env.SCREENSHOT_BASE_URL ?? "http://localhost:4173";

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 860 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(90_000);

  const shot = async (name) => {
    await page.screenshot({ path: resolve(OUT, name), fullPage: true });
    console.log("captured", name);
  };

  // 1. Join screen
  await page.goto(BASE);
  await page.getByRole("heading", { name: /join your class/i }).waitFor();
  await shot("01-join.png");

  // Join the seeded course.
  await page.getByLabel(/class code/i).fill("BIO101");
  await page.getByLabel(/display name/i).fill("Maria Santos");
  await page.getByRole("button", { name: /join class/i }).click();
  await page.getByRole("heading", { name: /welcome, maria/i }).waitFor();
  await shot("02-course-home.png");

  // 3. Upload screen (shows the real ingested documents)
  await page.goto(`${BASE}/upload`);
  await page.getByText("cell-structure-and-function.pdf").waitFor();
  await shot("03-upload.png");

  // 4. Ask a grounded question
  await page.goto(`${BASE}/ask`);
  await page.getByLabel(/your question/i).fill("What does the cell membrane do?");
  await page.getByRole("button", { name: /send question/i }).click();
  // Wait for the answer (the "Thinking…" indicator is replaced by the sources disclosure).
  await page.getByText(/sources \(/i).waitFor();
  await page.getByText(/sources \(/i).click(); // expand citations
  await shot("04-ask.png");

  // 5. Generate, take, and submit a quiz
  await page.goto(`${BASE}/quiz`);
  await page.getByLabel(/topic/i).fill("photosynthesis");
  await page.getByRole("button", { name: /generate quiz/i }).click();
  await page.getByRole("button", { name: /submit answers/i }).waitFor();
  // Answer each question with a varied option so the demo attempt reflects
  // realistic mixed performance rather than an all-wrong-by-construction run.
  const groups = await page.locator("fieldset").all();
  for (let i = 0; i < groups.length; i++) {
    const radios = groups[i].locator('input[type="radio"]');
    const count = await radios.count();
    await radios.nth(i % count).check();
  }
  await page.getByRole("button", { name: /submit answers/i }).click();
  await page.getByText(/you scored/i).waitFor();
  await shot("05-quiz-results.png");

  // 6. Progress screen (now has one attempt)
  await page.goto(`${BASE}/progress`);
  await page.getByRole("heading", { name: /your progress/i }).waitFor();
  await page.getByText(/quizzes taken/i).waitFor();
  await shot("06-progress.png");

  await browser.close();
  console.log("all screenshots written to", OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

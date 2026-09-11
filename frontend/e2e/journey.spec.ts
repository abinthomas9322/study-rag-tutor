import { expect, test } from "@playwright/test";

/**
 * The whole product, end to end, against the real stack: join the seeded
 * BIO101 course, ask a question that must be answered from the real OpenStax
 * material with citations, then generate a quiz, score it, and see the attempt
 * land on the progress screen.
 */
const NAME = "E2E Student";

test("join → grounded answer → scored quiz → progress", async ({ page }) => {
  // --- Join the seeded class ---
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /join your class/i })).toBeVisible();
  await page.getByLabel(/class code/i).fill("BIO101");
  await page.getByLabel(/display name/i).fill(NAME);
  await page.getByRole("button", { name: /join class/i }).click();

  await expect(
    page.getByRole("heading", { name: new RegExp(`welcome, ${NAME}`, "i") }),
  ).toBeVisible();

  // --- The materials are the real ingested OpenStax chapters ---
  await page.goto("/upload");
  await expect(page.getByText("cell-structure-and-function.pdf")).toBeVisible();

  // --- Ask: real retrieval + real LLM, answer must carry a citations block ---
  await page.goto("/ask");
  await page.getByLabel(/your question/i).fill("What does the cell membrane do?");
  await page.getByRole("button", { name: /send question/i }).click();
  // The "Sources (n)" disclosure only renders once a grounded answer returns.
  await expect(page.getByText(/sources \(\d+\)/i)).toBeVisible({ timeout: 90_000 });

  // --- Quiz: generate, answer every question, submit, see a score ---
  await page.goto("/quiz");
  await page.getByLabel(/topic/i).fill("photosynthesis");
  await page.getByRole("button", { name: /generate quiz/i }).click();

  const submit = page.getByRole("button", { name: /submit answers/i });
  await expect(submit).toBeVisible({ timeout: 90_000 });

  const questions = page.locator("fieldset");
  const count = await questions.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    await questions.nth(i).locator('input[type="radio"]').first().check();
  }
  await submit.click();

  await expect(page.getByText(/you scored/i)).toBeVisible();
  await expect(page.getByText(/^\d+ \/ \d+$/)).toBeVisible();

  // --- Progress: the attempt we just made is reflected ---
  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: /your progress/i })).toBeVisible();
  // The empty state is gone and the stats + history now render.
  await expect(page.getByText(/no quizzes yet/i)).toHaveCount(0);
  await expect(page.getByText(/quizzes taken/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: /history/i })).toBeVisible();
});

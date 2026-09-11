import { expect, test } from "@playwright/test";

/**
 * The unhappy paths: route guards for an unauthenticated visitor, a friendly
 * message for an unknown class code, client-side form validation, and non-PDF
 * rejection on the upload screen. None of these touch the LLM.
 */

test("guarded routes redirect a visitor with no session back to join", async ({ page }) => {
  for (const path of ["/course", "/upload", "/ask", "/quiz", "/progress"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: /join your class/i })).toBeVisible();
    await expect(page).toHaveURL(/\/$/);
  }
});

test("joining with an unknown class code shows a helpful message", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/class code/i).fill("NOPE999");
  await page.getByLabel(/display name/i).fill("Nobody");
  await page.getByRole("button", { name: /join class/i }).click();

  await expect(page.getByRole("alert")).toContainText(/doesn't exist yet/i);
  await expect(page).toHaveURL(/\/$/); // stayed on the join screen
});

test("the join form validates empty fields client-side", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /join class/i }).click();

  // exact: true avoids matching the intro paragraph, which also contains
  // "Enter your class code" as its opening words.
  await expect(page.getByText("Enter your class code", { exact: true })).toBeVisible();
  await expect(page.getByText("Enter a display name", { exact: true })).toBeVisible();
});

test("the upload screen rejects a non-PDF file", async ({ page }) => {
  // Establish a session by joining first.
  await page.goto("/");
  await page.getByLabel(/class code/i).fill("BIO101");
  await page.getByLabel(/display name/i).fill("Upload Tester");
  await page.getByRole("button", { name: /join class/i }).click();
  await expect(page.getByRole("heading", { name: /welcome, upload tester/i })).toBeVisible();

  await page.goto("/upload");
  await page.setInputFiles("#file-upload", {
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("this is not a pdf"),
  });

  await expect(page.getByRole("alert")).toContainText(/skipped non-pdf file\(s\): notes\.txt/i);
});

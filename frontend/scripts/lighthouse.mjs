/**
 * Measure Lighthouse scores for the production build, on every real screen.
 *
 * Prerequisites (a real run — no mocking):
 *   1. Backend on :8000 with the seeded BIO101 course (python -m seed.seed_demo).
 *   2. Frontend production build served by `vite preview` on :4173 (which
 *      proxies /api to the backend — see vite.config.ts).
 *
 * Lighthouse and a headless-Chrome driver are intentionally NOT committed
 * dependencies (they aren't needed for the build, tests, or CI). Install them
 * ad-hoc, the same way as the screenshot script:
 *
 *   npm i --no-save lighthouse puppeteer-core
 *   node scripts/lighthouse.mjs
 *
 * The authenticated screens (everything except "join") need a session in
 * localStorage, so the script joins the seeded course via the real API first
 * and seeds that session before auditing.
 *
 * Output: a Markdown summary on stdout, plus the full JSON reports under
 * docs/lighthouse/ for the record.
 */
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { mkdir, writeFile } from "node:fs/promises";

import lighthouse from "lighthouse";
import puppeteer from "puppeteer-core";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "../../docs/lighthouse");
const BASE = process.env.LH_BASE_URL ?? "http://localhost:4173";

// The system Chrome installs — override with CHROME_PATH if yours differs.
const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

const ROUTES = [
  { path: "/", name: "join" },
  { path: "/course", name: "course-home" },
  { path: "/upload", name: "upload" },
  { path: "/ask", name: "ask" },
  { path: "/quiz", name: "quiz" },
  { path: "/progress", name: "progress" },
];

const CATEGORIES = ["performance", "accessibility", "best-practices", "seo"];

async function joinDemoCourse() {
  const res = await fetch(`${BASE}/api/courses/BIO101/join`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ display_name: "Lighthouse Audit" }),
  });
  if (!res.ok) throw new Error(`join failed: ${res.status} ${await res.text()}`);
  return res.json();
}

function pct(score) {
  return Math.round((score ?? 0) * 100);
}

async function main() {
  await mkdir(OUT, { recursive: true });

  const student = await joinDemoCourse();
  const session = JSON.stringify({ courseId: "BIO101", student });

  const executablePath = CHROME_CANDIDATES.find(Boolean);
  const browser = await puppeteer.launch({
    executablePath,
    headless: true,
    args: ["--no-sandbox", "--disable-gpu"],
  });

  // Warm the preview server's module cache and the browser's disk cache with a
  // throwaway load, so the first *measured* route isn't unfairly penalised for
  // a cold start that a real returning visitor never sees.
  const warmup = await browser.newPage();
  await warmup.goto(`${BASE}/`, { waitUntil: "networkidle0" });
  await warmup.close();

  const rows = [];
  try {
    for (const route of ROUTES) {
      const page = await browser.newPage();
      // Seed the session before any app code runs, so the guarded routes render
      // instead of redirecting back to /.
      await page.evaluateOnNewDocument((value) => {
        window.localStorage.setItem("study-rag-session", value);
      }, session);

      const url = `${BASE}${route.path}`;
      const { lhr } = await lighthouse(
        url,
        {
          output: "json",
          logLevel: "error",
          onlyCategories: CATEGORIES,
          disableStorageReset: true, // keep the seeded localStorage
          formFactor: "desktop",
          screenEmulation: { disabled: true },
        },
        undefined,
        page,
      );

      await writeFile(resolve(OUT, `${route.name}.json`), JSON.stringify(lhr, null, 2));

      const scores = Object.fromEntries(CATEGORIES.map((c) => [c, pct(lhr.categories[c]?.score)]));
      rows.push({ route: route.path, ...scores });
      await page.close();
      console.error(`audited ${route.path}`, scores);
    }
  } finally {
    await browser.close();
  }

  const header = `| Route | Performance | Accessibility | Best practices | SEO |\n|---|---|---|---|---|`;
  const body = rows
    .map(
      (r) =>
        `| \`${r.route}\` | ${r.performance} | ${r.accessibility} | ${r["best-practices"]} | ${r.seo} |`,
    )
    .join("\n");
  const table = `${header}\n${body}\n`;

  await writeFile(resolve(OUT, "summary.md"), table);
  console.log("\n" + table);

  const failing = rows.filter(
    (r) => Math.min(r.performance, r.accessibility, r["best-practices"]) < 90,
  );
  if (failing.length) {
    console.error(
      `\n${failing.length} route(s) below 90 on a core category:`,
      failing.map((r) => r.route).join(", "),
    );
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

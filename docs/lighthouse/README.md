# Lighthouse audit

Scores for the **production build** of the frontend, measured on every screen.
The UI standard for this repo (§9b) is **≥ 90** on performance, accessibility,
and best-practices.

## Results (2026-09-03)

| Route | Performance | Accessibility | Best practices | SEO |
|---|---|---|---|---|
| `/` (join) | 97 | 100 | 100 | 91 |
| `/course` | 97 | 100 | 100 | 91 |
| `/upload` | 97 | 100 | 100 | 91 |
| `/ask` | 97 | 100 | 100 | 91 |
| `/quiz` | 97 | 100 | 100 | 91 |
| `/progress` | 96 | 100 | 100 | 91 |

`summary.md` is the exact table the script last emitted; the full per-route
JSON reports are written next to it but are git-ignored (large and regenerable).

## Methodology

- Target: `vite preview` serving the real `npm run build` output on `:4173`,
  with the backend on `:8000` and the seeded **BIO101** course.
- Desktop form factor, no network/CPU throttling emulation.
- The authenticated screens need a session, so the script joins the seeded
  course through the real API and seeds `localStorage` before auditing.
- A throwaway page load warms the preview server and disk cache first, so the
  first measured route isn't charged for a cold start a returning visitor never
  pays.

## Reproduce

From `frontend/`, with the backend and preview server running:

```bash
npm i --no-save lighthouse puppeteer-core
node scripts/lighthouse.mjs
```

Lighthouse and its headless-Chrome driver are **not** committed dependencies —
they're only needed to regenerate this report, never for the build, tests, or
CI (same policy as `scripts/screenshots.mjs`).

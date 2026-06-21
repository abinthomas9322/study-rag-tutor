# 🚀 Deploy guide — Render (API) + Vercel (frontend)

Both have free tiers. The backend ships as a Docker image that **bakes in the
real OpenStax demo course** at build time, so the deployed app starts with
genuine data already indexed. On the free tier the disk is **ephemeral** — the
demo course is always present, but new uploads/quiz history reset on restart.

> Deploy the **backend first** so you have its URL for the frontend.

## 1. Backend → Render

1. Push the repo to GitHub (already done).
2. In the [Render dashboard](https://dashboard.render.com): **New → Web Service**
   (or **New → Blueprint** to use the committed `render.yaml`).
3. Connect this repo. If not using the blueprint, set:
   - **Runtime:** Docker
   - **Dockerfile path:** `backend/Dockerfile`
   - **Docker context:** `backend`
   - **Plan:** Free · **Health check path:** `/health`
4. Add environment variables:
   - `GROQ_API_KEY` = your Groq key
   - `CORS_ORIGINS` = `*` for now (tighten to your Vercel URL in step 3)
5. Create the service. The first build downloads the embedding model and seeds
   the course, so it takes a few minutes. When live, check
   `https://<your-api>.onrender.com/health` — it should look like:

   ```json
   {
     "status": "ok",
     "version": "0.1.0",
     "demo_seeded": true,
     "db_kind": "sqlite",
     "db_path": "tutor.db"
   }
   ```

   `demo_seeded: true` means the build's seed step produced a real BIO101
   record. If it's `false`, the seed failed silently — trigger a manual
   rebuild from the Render dashboard and read the build log.

## 2. Frontend → Vercel

1. In [Vercel](https://vercel.com/new): **Add New → Project**, import this repo.
2. Set **Root Directory** to `frontend` (framework auto-detects as Vite).
3. Add an environment variable:
   - `VITE_API_URL` = your Render API URL (e.g. `https://study-rag-tutor-api.onrender.com`)
4. Deploy. You'll get a URL like `https://study-rag-tutor.vercel.app`.

## 3. Lock down CORS (optional but recommended)

Back in Render, set `CORS_ORIGINS` to your exact Vercel URL and redeploy, so the
API only accepts requests from your frontend.

## 4. Try it

Open the Vercel URL, join class **BIO101**, and ask a question / take a quiz.

## Free-tier notes

- **Cold starts.** The Render free plan sleeps the service after ~15 min of
  inactivity. The first request after sleep takes ~30 s; subsequent ones are
  snappy. This is a free-tier trade-off — the paid plan removes it.
- **Ephemeral disk.** The SQLite file lives on the container's disk, so any
  uploaded PDFs and quiz history are wiped on restart / redeploy. The demo
  course is rebuilt into the image at every build, so it's always present.
- **One instance.** Free Render only allows one container, so the app isn't
  horizontally scalable on this tier. Plenty for a portfolio demo; for a real
  class you'd want a paid plan plus a persistent disk or a managed database.

## Updating the live demo link

After deploying, update the **Live demo** line in `README.md` with the Vercel
URL.

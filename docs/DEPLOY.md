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
   `https://<your-api>.onrender.com/health` → `{"status":"ok"}`.

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

> **Note:** the free Render service sleeps when idle, so the first request after
> a while has a ~30s cold start. Once warm it's snappy.

## Updating the live demo link

After deploying, update the **Live demo** line in `README.md` with the Vercel
URL.

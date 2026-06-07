# Backend image for the Study-Group RAG Tutor (build context: ./backend).
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App + RAG core + the committed demo PDFs.
COPY . .

# Store the SQLite file at /app/tutor.db (not the repo's nested default).
ENV DB_PATH=tutor.db

# Bake the real OpenStax demo course into the image: this downloads the small
# embedding model once at build time and indexes the chunks, so the deployed
# service starts fast with genuine data already present. (No API key needed —
# seeding only embeds locally.)
RUN python -m seed.seed_demo

# Render (and most hosts) inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]

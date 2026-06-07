/**
 * Tiny typed client for the backend API. In development, requests to /api are
 * proxied to the FastAPI server by Vite (see vite.config.ts).
 */

const API_BASE = "/api";

export interface HealthResponse {
  status: string;
}

/** Ping the backend liveness probe. Throws if the response isn't ok. */
export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { signal });
  if (!res.ok) {
    throw new Error(`backend returned ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}

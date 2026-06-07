/**
 * Tiny typed client for the backend API. In development, requests to /api are
 * proxied to the FastAPI server by Vite (see vite.config.ts).
 */

const API_BASE = "/api";

/** An error carrying the HTTP status, so callers can branch on it (e.g. 404). */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(res: Response): Promise<ApiError> {
  // FastAPI returns { detail: ... }; fall back to the status text if absent.
  let detail = res.statusText;
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    // non-JSON body — keep the status text
  }
  return new ApiError(res.status, detail);
}

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

export interface Student {
  id: number;
  course_id: string;
  display_name: string;
  joined_at: string;
}

/** Join a course as a student (idempotent server-side). Throws ApiError on failure. */
export async function joinCourse(courseId: string, displayName: string): Promise<Student> {
  const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!res.ok) {
    throw await parseError(res);
  }
  return (await res.json()) as Student;
}

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

export interface CourseDocument {
  id: string;
  course_id: string;
  filename: string;
  num_chunks: number;
  uploaded_at: string;
}

/** List the documents uploaded to a course. */
export async function listDocuments(courseId: string): Promise<CourseDocument[]> {
  const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/documents`);
  if (!res.ok) {
    throw await parseError(res);
  }
  return (await res.json()) as CourseDocument[];
}

/** Upload one PDF into a course; it is chunked, embedded, and indexed server-side. */
export async function uploadDocument(courseId: string, file: File): Promise<CourseDocument> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/documents`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw await parseError(res);
  }
  return (await res.json()) as CourseDocument;
}

export interface Source {
  document_id: string;
  text: string;
  distance: number;
}

export interface Answer {
  answer: string;
  sources: Source[];
}

/** Ask a question grounded in a course's materials; returns the answer + sources. */
export async function askQuestion(courseId: string, question: string): Promise<Answer> {
  const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    throw await parseError(res);
  }
  return (await res.json()) as Answer;
}

export interface QuizQuestion {
  stem: string;
  options: string[];
}

export interface Quiz {
  id: string | null; // null when the course has no materials
  questions: QuizQuestion[];
  sources: Source[];
}

export interface QuestionResult {
  stem: string;
  options: string[];
  your_answer: number;
  correct_index: number;
  is_correct: boolean;
  explanation: string;
}

export interface Attempt {
  id: number;
  quiz_id: string;
  student_id: number;
  score: number;
  total: number;
  submitted_at: string;
  results: QuestionResult[];
}

/** Generate a practice quiz grounded in a course's materials (answer key withheld). */
export async function generateQuiz(
  courseId: string,
  opts: { topic?: string | null; numQuestions: number },
): Promise<Quiz> {
  const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/quiz`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic: opts.topic ?? null, num_questions: opts.numQuestions }),
  });
  if (!res.ok) {
    throw await parseError(res);
  }
  return (await res.json()) as Quiz;
}

/** Submit answers for a quiz; returns the score and per-question review. */
export async function submitAttempt(
  courseId: string,
  quizId: string,
  opts: { studentId: number; answers: number[] },
): Promise<Attempt> {
  const res = await fetch(
    `${API_BASE}/courses/${encodeURIComponent(courseId)}/quizzes/${encodeURIComponent(quizId)}/attempts`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: opts.studentId, answers: opts.answers }),
    },
  );
  if (!res.ok) {
    throw await parseError(res);
  }
  return (await res.json()) as Attempt;
}

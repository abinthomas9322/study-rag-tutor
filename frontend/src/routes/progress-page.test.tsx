import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchHealth, listAttempts, type AttemptSummary } from "@/api/client";
import { renderApp } from "@/test/utils";

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return { ...actual, fetchHealth: vi.fn(), listAttempts: vi.fn() };
});

const mockedAttempts = vi.mocked(listAttempts);

const ATTEMPTS: AttemptSummary[] = [
  { id: 2, quiz_id: "q2", topic: "mitosis", score: 5, total: 5, submitted_at: "2026-06-07" },
  { id: 1, quiz_id: "q1", topic: null, score: 1, total: 2, submitted_at: "2026-06-06" },
];

beforeEach(() => {
  vi.mocked(fetchHealth).mockResolvedValue({ status: "ok" });
  localStorage.setItem(
    "study-rag-session",
    JSON.stringify({
      courseId: "CS101",
      student: { id: 1, course_id: "CS101", display_name: "Alex", joined_at: "2026-01-01" },
    }),
  );
});

afterEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
});

describe("ProgressPage", () => {
  it("redirects to join when there is no session", () => {
    localStorage.clear();
    mockedAttempts.mockResolvedValue([]);
    renderApp("/progress");
    expect(screen.getByRole("heading", { level: 1, name: /join your class/i })).toBeInTheDocument();
  });

  it("shows an empty state with a link to take a quiz", async () => {
    mockedAttempts.mockResolvedValue([]);
    renderApp("/progress");
    expect(await screen.findByText(/no quizzes yet/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /take a quiz/i })).toBeInTheDocument();
  });

  it("shows stats and the attempt history", async () => {
    mockedAttempts.mockResolvedValue(ATTEMPTS);
    renderApp("/progress");

    // Quizzes taken = 2.
    expect(await screen.findByText("2")).toBeInTheDocument();
    // Average of 100% and 50% = 75% (unique to the stats row).
    expect(screen.getByText("75%")).toBeInTheDocument();
    // Best = 100% — also appears as a row percentage, so allow more than one.
    expect(screen.getAllByText("100%").length).toBeGreaterThan(0);

    // History rows: topic shown, null topic falls back to "General quiz".
    expect(screen.getByText("mitosis")).toBeInTheDocument();
    expect(screen.getByText(/general quiz/i)).toBeInTheDocument();
    expect(screen.getByText("5 / 5")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("shows an error state when loading fails", async () => {
    mockedAttempts.mockRejectedValue(new Error("boom"));
    renderApp("/progress");
    expect(await screen.findByText(/couldn't load your progress/i)).toBeInTheDocument();
  });
});

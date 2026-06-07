import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  fetchHealth,
  generateQuiz,
  submitAttempt,
  type Attempt,
  type Quiz,
} from "@/api/client";
import { renderApp } from "@/test/utils";

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    fetchHealth: vi.fn(),
    generateQuiz: vi.fn(),
    submitAttempt: vi.fn(),
  };
});

const mockedGenerate = vi.mocked(generateQuiz);
const mockedSubmit = vi.mocked(submitAttempt);

const QUIZ: Quiz = {
  id: "quiz-1",
  questions: [
    { stem: "What is 2 + 2?", options: ["3", "4", "5", "6"] },
    { stem: "Capital of France?", options: ["Berlin", "Paris", "Rome", "Madrid"] },
  ],
  sources: [],
};

const ATTEMPT: Attempt = {
  id: 1,
  quiz_id: "quiz-1",
  student_id: 1,
  score: 1,
  total: 2,
  submitted_at: "2026-06-07",
  results: [
    {
      stem: "What is 2 + 2?",
      options: ["3", "4", "5", "6"],
      your_answer: 1,
      correct_index: 1,
      is_correct: true,
      explanation: "Two plus two is four.",
    },
    {
      stem: "Capital of France?",
      options: ["Berlin", "Paris", "Rome", "Madrid"],
      your_answer: 0,
      correct_index: 1,
      is_correct: false,
      explanation: "Paris is the capital of France.",
    },
  ],
};

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

describe("QuizPage", () => {
  it("redirects to join when there is no session", () => {
    localStorage.clear();
    renderApp("/quiz");
    expect(screen.getByRole("heading", { level: 1, name: /join your class/i })).toBeInTheDocument();
  });

  it("shows the config form first", () => {
    renderApp("/quiz");
    expect(screen.getByRole("button", { name: /generate quiz/i })).toBeInTheDocument();
  });

  it("shows an upload prompt when the course has no materials", async () => {
    const user = userEvent.setup();
    mockedGenerate.mockResolvedValue({ id: null, questions: [], sources: [] });
    renderApp("/quiz");

    await user.click(screen.getByRole("button", { name: /generate quiz/i }));

    expect(await screen.findByText(/no materials to quiz on yet/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /upload materials/i })).toBeInTheDocument();
  });

  it("generates, takes, submits, and shows the score with review", async () => {
    const user = userEvent.setup();
    mockedGenerate.mockResolvedValue(QUIZ);
    mockedSubmit.mockResolvedValue(ATTEMPT);
    renderApp("/quiz");

    await user.click(screen.getByRole("button", { name: /generate quiz/i }));

    // Taking phase: both questions render.
    expect(await screen.findByText(/what is 2 \+ 2\?/i)).toBeInTheDocument();
    const submit = screen.getByRole("button", { name: /submit answers/i });
    expect(submit).toBeDisabled(); // nothing answered yet

    await user.click(screen.getByRole("radio", { name: "4" }));
    await user.click(screen.getByRole("radio", { name: "Berlin" }));
    expect(submit).toBeEnabled();

    await user.click(submit);

    // Results phase.
    expect(await screen.findByText("1 / 2")).toBeInTheDocument();
    expect(mockedSubmit).toHaveBeenCalledWith("CS101", "quiz-1", {
      studentId: 1,
      answers: [1, 0],
    });
    expect(screen.getByText(/paris is the capital of france/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /take another quiz/i })).toBeInTheDocument();
  });

  it("shows an error if generation fails", async () => {
    const user = userEvent.setup();
    mockedGenerate.mockRejectedValue(new ApiError(502, "the model returned no quiz questions"));
    renderApp("/quiz");

    await user.click(screen.getByRole("button", { name: /generate quiz/i }));

    expect(await screen.findByText(/no quiz questions/i)).toBeInTheDocument();
  });

  it("sends the chosen topic and question count", async () => {
    const user = userEvent.setup();
    mockedGenerate.mockResolvedValue(QUIZ);
    renderApp("/quiz");

    await user.type(screen.getByLabelText(/topic/i), "arithmetic");
    await user.selectOptions(screen.getByLabelText(/number of questions/i), "10");
    await user.click(screen.getByRole("button", { name: /generate quiz/i }));

    await screen.findByText(/what is 2 \+ 2\?/i);
    expect(mockedGenerate).toHaveBeenCalledWith("CS101", { topic: "arithmetic", numQuestions: 10 });
  });
});

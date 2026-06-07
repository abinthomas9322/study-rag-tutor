import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  askQuestion,
  fetchHealth,
  listDocuments,
  type Answer,
  type CourseDocument,
} from "@/api/client";
import { renderApp } from "@/test/utils";

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    fetchHealth: vi.fn(),
    listDocuments: vi.fn(),
    askQuestion: vi.fn(),
  };
});

const mockedAsk = vi.mocked(askQuestion);
const mockedList = vi.mocked(listDocuments);

const DOC: CourseDocument = {
  id: "doc-1",
  course_id: "CS101",
  filename: "cells.pdf",
  num_chunks: 5,
  uploaded_at: "2026-06-07",
};

const ANSWER: Answer = {
  answer: "The cell membrane controls what enters the cell [Source 1].",
  sources: [
    { document_id: "doc-1", text: "The cell membrane controls what enters", distance: 0.1 },
  ],
};

beforeEach(() => {
  vi.mocked(fetchHealth).mockResolvedValue({ status: "ok" });
  mockedList.mockResolvedValue([DOC]);
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

describe("AskPage", () => {
  it("redirects to join when there is no session", () => {
    localStorage.clear();
    renderApp("/ask");
    expect(screen.getByRole("heading", { level: 1, name: /join your class/i })).toBeInTheDocument();
  });

  it("shows an empty state before any question", () => {
    renderApp("/ask");
    expect(screen.getByText(/ask your first question/i)).toBeInTheDocument();
  });

  it("disables send until a question is typed", async () => {
    const user = userEvent.setup();
    renderApp("/ask");
    const send = screen.getByRole("button", { name: /send question/i });
    expect(send).toBeDisabled();
    await user.type(screen.getByLabelText(/your question/i), "What does the membrane do?");
    expect(send).toBeEnabled();
  });

  it("asks a question and renders the grounded answer with a mapped source", async () => {
    const user = userEvent.setup();
    mockedAsk.mockResolvedValue(ANSWER);
    renderApp("/ask");

    await user.type(screen.getByLabelText(/your question/i), "What does the membrane do?");
    await user.click(screen.getByRole("button", { name: /send question/i }));

    expect(
      await screen.findByText(/the cell membrane controls what enters the cell/i),
    ).toBeInTheDocument();
    expect(mockedAsk).toHaveBeenCalledWith("CS101", "What does the membrane do?");

    // The source maps document_id -> filename from the documents list.
    const sources = screen.getByText(/sources \(1\)/i);
    await user.click(sources);
    expect(screen.getByText(/source 1 · cells\.pdf/i)).toBeInTheDocument();
  });

  it("shows the question immediately and an error if the request fails", async () => {
    const user = userEvent.setup();
    mockedAsk.mockRejectedValue(new ApiError(500, "the model is unavailable"));
    renderApp("/ask");

    await user.type(screen.getByLabelText(/your question/i), "Anything?");
    await user.click(screen.getByRole("button", { name: /send question/i }));

    expect(await screen.findByText(/the model is unavailable/i)).toBeInTheDocument();
    expect(screen.getByText("Anything?")).toBeInTheDocument();
  });

  it("clears the input after sending", async () => {
    const user = userEvent.setup();
    mockedAsk.mockResolvedValue(ANSWER);
    renderApp("/ask");

    const input = screen.getByLabelText(/your question/i);
    await user.type(input, "What does the membrane do?");
    await user.click(screen.getByRole("button", { name: /send question/i }));

    // "enters the cell" is unique to the answer (the source snippet ends at "enters").
    await screen.findByText(/enters the cell/i);
    expect(input).toHaveValue("");
  });
});

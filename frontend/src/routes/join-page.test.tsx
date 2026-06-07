import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchHealth, joinCourse, type Student } from "@/api/client";
import { renderApp } from "@/test/utils";

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return { ...actual, joinCourse: vi.fn(), fetchHealth: vi.fn() };
});

const mockedJoin = vi.mocked(joinCourse);
const mockedHealth = vi.mocked(fetchHealth);

const STUDENT: Student = {
  id: 7,
  course_id: "CS101",
  display_name: "Alex Kim",
  joined_at: "2026-01-01T00:00:00",
};

beforeEach(() => {
  mockedHealth.mockResolvedValue({ status: "ok" });
});

afterEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
});

describe("JoinPage", () => {
  it("shows validation errors and does not call the API on empty submit", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("button", { name: /join class/i }));

    // Validation messages render in alert regions; query those to avoid matching
    // the page subtitle, which also contains the phrase "enter your class code".
    const alerts = await screen.findAllByRole("alert");
    const alertText = alerts.map((a) => a.textContent).join(" ");
    expect(alertText).toContain("Enter your class code");
    expect(alertText).toContain("Enter a display name");
    expect(mockedJoin).not.toHaveBeenCalled();
  });

  it("joins, persists the session, and navigates to the course home", async () => {
    const user = userEvent.setup();
    mockedJoin.mockResolvedValue(STUDENT);
    renderApp("/");

    await user.type(screen.getByLabelText(/class code/i), "CS101");
    await user.type(screen.getByLabelText(/display name/i), "Alex Kim");
    await user.click(screen.getByRole("button", { name: /join class/i }));

    expect(await screen.findByText(/welcome, alex kim/i)).toBeInTheDocument();
    expect(mockedJoin).toHaveBeenCalledWith("CS101", "Alex Kim");
    expect(localStorage.getItem("study-rag-session")).toContain("CS101");
  });

  it("shows a friendly message when the class doesn't exist (404)", async () => {
    const user = userEvent.setup();
    mockedJoin.mockRejectedValue(new ApiError(404, "course 'NOPE' not found"));
    renderApp("/");

    await user.type(screen.getByLabelText(/class code/i), "NOPE");
    await user.type(screen.getByLabelText(/display name/i), "Alex");
    await user.click(screen.getByRole("button", { name: /join class/i }));

    expect(await screen.findByText(/doesn't exist yet/i)).toBeInTheDocument();
  });

  it("disables the button while the request is in flight", async () => {
    const user = userEvent.setup();
    mockedJoin.mockReturnValue(new Promise(() => {})); // never resolves
    renderApp("/");

    await user.type(screen.getByLabelText(/class code/i), "CS101");
    await user.type(screen.getByLabelText(/display name/i), "Alex");
    await user.click(screen.getByRole("button", { name: /join class/i }));

    expect(await screen.findByRole("button", { name: /joining/i })).toBeDisabled();
  });
});

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";

import { fetchHealth, joinCourse, type Student } from "@/api/client";
import { renderApp } from "@/test/utils";

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return { ...actual, joinCourse: vi.fn(), fetchHealth: vi.fn() };
});

const SESSION = {
  courseId: "CS101",
  student: { id: 1, course_id: "CS101", display_name: "Alex", joined_at: "2026-01-01" } as Student,
};

beforeEach(() => {
  vi.mocked(fetchHealth).mockResolvedValue({ status: "ok" });
  vi.mocked(joinCourse);
});

afterEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  document.documentElement.classList.remove("dark");
});

describe("App shell + routing", () => {
  it("renders the product name in the header", () => {
    renderApp("/");
    expect(screen.getAllByText(/study-group rag tutor/i).length).toBeGreaterThan(0);
  });

  it("shows the join screen at the index route", () => {
    renderApp("/");
    expect(screen.getByRole("heading", { level: 1, name: /join your class/i })).toBeInTheDocument();
  });

  it("has no detectable accessibility violations on the join screen", async () => {
    const { container } = renderApp("/");
    const results = await axe(container, { rules: { "color-contrast": { enabled: false } } });
    expect(results.violations).toEqual([]);
  });

  it("toggles between light and dark themes", async () => {
    const user = userEvent.setup();
    renderApp("/");
    expect(document.documentElement).not.toHaveClass("dark");
    await user.click(screen.getByRole("button", { name: /switch to dark theme/i }));
    expect(document.documentElement).toHaveClass("dark");
  });

  it("redirects to the join screen when visiting /course without a session", () => {
    renderApp("/course");
    expect(screen.getByRole("heading", { level: 1, name: /join your class/i })).toBeInTheDocument();
  });

  it("redirects a joined student from the index route to the course home", () => {
    localStorage.setItem("study-rag-session", JSON.stringify(SESSION));
    renderApp("/");
    expect(screen.getByRole("heading", { level: 1, name: /welcome, alex/i })).toBeInTheDocument();
  });
});

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";

import App from "@/App";
import { fetchHealth } from "@/api/client";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/api/client");

beforeEach(() => {
  vi.mocked(fetchHealth).mockResolvedValue({ status: "ok" });
});

afterEach(() => {
  vi.resetAllMocks();
  document.documentElement.classList.remove("dark");
  localStorage.clear();
});

describe("App shell", () => {
  it("renders the product name and headline", () => {
    renderWithProviders(<App />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/study together/i);
    expect(screen.getAllByText(/study-group rag tutor/i).length).toBeGreaterThan(0);
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = renderWithProviders(<App />);
    // color-contrast can't run under jsdom (no canvas); it's covered by
    // Lighthouse against the real production build instead.
    const results = await axe(container, {
      rules: { "color-contrast": { enabled: false } },
    });
    expect(results.violations).toEqual([]);
  });

  it("toggles between light and dark themes", async () => {
    const user = userEvent.setup();
    renderWithProviders(<App />);

    expect(document.documentElement).not.toHaveClass("dark");
    await user.click(screen.getByRole("button", { name: /switch to dark theme/i }));
    expect(document.documentElement).toHaveClass("dark");
    await user.click(screen.getByRole("button", { name: /switch to light theme/i }));
    expect(document.documentElement).not.toHaveClass("dark");
  });
});

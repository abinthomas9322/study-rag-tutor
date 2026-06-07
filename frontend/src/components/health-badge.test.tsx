import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchHealth } from "@/api/client";
import { HealthBadge } from "@/components/health-badge";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/api/client");
const mockedFetchHealth = vi.mocked(fetchHealth);

afterEach(() => {
  vi.resetAllMocks();
});

describe("HealthBadge", () => {
  it("shows a loading state first", () => {
    mockedFetchHealth.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithProviders(<HealthBadge />);
    expect(screen.getByText(/connecting/i)).toBeInTheDocument();
  });

  it("shows the online state when the backend responds ok", async () => {
    mockedFetchHealth.mockResolvedValue({ status: "ok" });
    renderWithProviders(<HealthBadge />);
    expect(await screen.findByText(/backend ok/i)).toBeInTheDocument();
  });

  it("shows the offline state when the request fails", async () => {
    mockedFetchHealth.mockRejectedValue(new Error("network down"));
    renderWithProviders(<HealthBadge />);
    // The badge retries once with backoff before settling, so allow extra time.
    expect(
      await screen.findByText(/backend offline/i, undefined, { timeout: 5000 }),
    ).toBeInTheDocument();
  });
});

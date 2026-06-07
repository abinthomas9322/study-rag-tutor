import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

import { ThemeProvider } from "@/components/theme-provider";

/** Render a component wrapped in the app's providers (theme + a fresh query client). */
export function renderWithProviders(ui: ReactElement): RenderResult {
  // A fresh client per render keeps tests isolated and disables retries so
  // error states surface immediately.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </ThemeProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}

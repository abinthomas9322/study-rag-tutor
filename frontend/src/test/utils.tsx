import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { ThemeProvider } from "@/components/theme-provider";
import { routes } from "@/router";
import { SessionProvider } from "@/session/session-context";

function makeClient(): QueryClient {
  // Fresh per render, no retries — error states surface immediately in tests.
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={makeClient()}>
        <SessionProvider>{children}</SessionProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

/** Render a standalone component wrapped in the app's non-routing providers. */
export function renderWithProviders(ui: ReactElement): RenderResult {
  return render(ui, { wrapper: Providers });
}

/** Wrapper for renderHook and similar — exposes the app providers as a component. */
export { Providers };

/** Render the real route tree in a memory router at `initialPath`. */
export function renderApp(initialPath = "/"): RenderResult {
  const router = createMemoryRouter(routes, { initialEntries: [initialPath] });
  return render(
    <Providers>
      <RouterProvider router={router} />
    </Providers>,
  );
}

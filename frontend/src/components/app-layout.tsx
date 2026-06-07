import { GraduationCap } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

import { HealthBadge } from "@/components/health-badge";
import { ThemeToggle } from "@/components/theme-toggle";

/** App chrome shared by every route: header with status + theme, and a footer. */
export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <GraduationCap className="size-6 text-primary" aria-hidden="true" />
            <span>Study-Group RAG Tutor</span>
          </Link>
          <div className="flex items-center gap-3">
            <HealthBadge />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="container flex-1 py-12">
        <Outlet />
      </main>

      <footer className="border-t py-6">
        <div className="container text-center text-sm text-muted-foreground">
          Built for study groups · grounded answers, real citations
        </div>
      </footer>
    </div>
  );
}

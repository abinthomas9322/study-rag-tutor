import { LogOut, MessagesSquare, ListChecks, Upload } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useSession } from "@/session/session-context";

interface Action {
  icon: LucideIcon;
  title: string;
  description: string;
  to?: string; // present when the destination screen exists
}

// Upload is live (slice 5.3); the rest land in later slices and are shown as
// honest "coming soon" cards rather than faking functionality.
const ACTIONS: Action[] = [
  {
    icon: Upload,
    title: "Upload materials",
    description: "Add course PDFs to the shared space.",
    to: "/upload",
  },
  {
    icon: MessagesSquare,
    title: "Ask questions",
    description: "Get answers cited from the materials.",
  },
  {
    icon: ListChecks,
    title: "Practice quizzes",
    description: "Generate and take scored quizzes.",
  },
];

export function CourseHome() {
  const { session, endSession } = useSession();
  const navigate = useNavigate();

  // No session → send the student back to the join screen.
  if (!session) return <Navigate to="/" replace />;

  const { courseId, student } = session;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome, {student.display_name}</h1>
          <p className="mt-2 text-muted-foreground">
            You're in class <span className="font-medium text-foreground">{courseId}</span>.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            endSession();
            navigate("/");
          }}
        >
          <LogOut aria-hidden="true" />
          Leave class
        </Button>
      </div>

      <section aria-labelledby="actions-heading" className="mt-10">
        <h2 id="actions-heading" className="text-lg font-semibold">
          What's next
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {ACTIONS.map((action) => {
            const card = (
              <Card
                className={cn(
                  "h-full transition-colors",
                  action.to ? "focus-within:border-primary hover:border-primary" : "opacity-80",
                )}
              >
                <CardHeader>
                  <action.icon className="size-6 text-primary" aria-hidden="true" />
                  <CardTitle className="text-base">{action.title}</CardTitle>
                  <CardDescription>{action.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-xs font-medium text-muted-foreground">
                    {action.to ? "Open" : "Coming soon"}
                  </span>
                </CardContent>
              </Card>
            );
            return action.to ? (
              <Link
                key={action.title}
                to={action.to}
                className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                {card}
              </Link>
            ) : (
              <div key={action.title}>{card}</div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

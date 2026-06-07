import { LogOut, MessagesSquare, ListChecks, Upload } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSession } from "@/session/session-context";

// The actions that land in later slices (5.3–5.6); shown disabled for now so
// the course home is honest about what's coming without faking functionality.
const UPCOMING = [
  { icon: Upload, title: "Upload materials", description: "Add course PDFs to the shared space." },
  {
    icon: MessagesSquare,
    title: "Ask questions",
    description: "Get answers cited from the materials.",
  },
  { icon: ListChecks, title: "Practice quizzes", description: "Generate and take scored quizzes." },
] as const;

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

      <section aria-labelledby="next-heading" className="mt-10">
        <h2 id="next-heading" className="text-lg font-semibold">
          What's next
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {UPCOMING.map((item) => (
            <Card key={item.title} className="h-full opacity-80">
              <CardHeader>
                <item.icon className="size-6 text-primary" aria-hidden="true" />
                <CardTitle className="text-base">{item.title}</CardTitle>
                <CardDescription>{item.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <span className="text-xs font-medium text-muted-foreground">Coming soon</span>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

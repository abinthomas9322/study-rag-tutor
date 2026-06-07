import { useQuery } from "@tanstack/react-query";
import { Award, ListChecks, TrendingUp } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import { listAttempts, type AttemptSummary } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useSession } from "@/session/session-context";

function percent(score: number, total: number): number {
  return total === 0 ? 0 : Math.round((score / total) * 100);
}

function Stat({ icon: Icon, label, value }: { icon: typeof Award; label: string; value: string }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 py-5">
        <Icon className="size-6 text-primary" aria-hidden="true" />
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function ProgressPage() {
  const { session } = useSession();
  const courseId = session?.courseId ?? "";
  const studentId = session?.student.id ?? 0;

  const attempts = useQuery({
    queryKey: ["attempts", courseId, studentId],
    queryFn: () => listAttempts(courseId, studentId),
    enabled: Boolean(session),
  });

  // No session → back to join.
  if (!session) return <Navigate to="/" replace />;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Your progress</h1>
          <p className="mt-2 text-muted-foreground">
            Your quiz history in class{" "}
            <span className="font-medium text-foreground">{courseId}</span>.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/course">Back to class</Link>
        </Button>
      </div>

      {attempts.isPending ? (
        <p className="mt-8 text-sm text-muted-foreground" role="status">
          Loading your progress…
        </p>
      ) : attempts.isError ? (
        <p className="mt-8 text-sm text-destructive" role="alert">
          Couldn't load your progress. Please try again.
        </p>
      ) : attempts.data.length === 0 ? (
        <Card className="mt-8">
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <ListChecks className="size-8 text-primary" aria-hidden="true" />
            <p className="font-medium">No quizzes yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Take your first practice quiz and your scores will show up here.
            </p>
            <Button asChild className="mt-2">
              <Link to="/quiz">Take a quiz</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <ProgressContent attempts={attempts.data} />
      )}
    </div>
  );
}

function ProgressContent({ attempts }: { attempts: AttemptSummary[] }) {
  const taken = attempts.length;
  const averagePct = Math.round(
    attempts.reduce((sum, a) => sum + percent(a.score, a.total), 0) / taken,
  );
  const bestPct = Math.max(...attempts.map((a) => percent(a.score, a.total)));

  return (
    <>
      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <Stat icon={ListChecks} label="Quizzes taken" value={String(taken)} />
        <Stat icon={TrendingUp} label="Average score" value={`${averagePct}%`} />
        <Stat icon={Award} label="Best score" value={`${bestPct}%`} />
      </div>

      <h2 className="mt-10 text-lg font-semibold">History</h2>
      <ul className="mt-4 space-y-2">
        {attempts.map((a) => (
          <li key={a.id} className="flex items-center gap-4 rounded-md border bg-card p-3">
            <div className="flex-1">
              <p className="font-medium">{a.topic ?? "General quiz"}</p>
              <p className="text-sm text-muted-foreground">{a.submitted_at.slice(0, 10)}</p>
            </div>
            <div className="text-right">
              <p className="font-semibold">
                {a.score} / {a.total}
              </p>
              <p className="text-sm text-muted-foreground">{percent(a.score, a.total)}%</p>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

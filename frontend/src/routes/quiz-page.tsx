import { CheckCircle2, CircleAlert, Loader2, Sparkles, XCircle } from "lucide-react";
import * as React from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError, generateQuiz, submitAttempt, type Attempt, type Quiz } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useSession } from "@/session/session-context";

type Phase = "config" | "taking" | "results";

const QUESTION_COUNTS = [3, 5, 10];

export function QuizPage() {
  const { session } = useSession();
  const [phase, setPhase] = React.useState<Phase>("config");
  const [topic, setTopic] = React.useState("");
  const [numQuestions, setNumQuestions] = React.useState(5);
  const [quiz, setQuiz] = React.useState<Quiz | null>(null);
  const [answers, setAnswers] = React.useState<(number | null)[]>([]);
  const [attempt, setAttempt] = React.useState<Attempt | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [noMaterials, setNoMaterials] = React.useState(false);

  const courseId = session?.courseId ?? "";
  const studentId = session?.student.id ?? 0;

  // No session → back to join.
  if (!session) return <Navigate to="/" replace />;

  function reset() {
    setPhase("config");
    setQuiz(null);
    setAnswers([]);
    setAttempt(null);
    setError(null);
    setNoMaterials(false);
  }

  async function handleGenerate(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNoMaterials(false);
    try {
      const result = await generateQuiz(courseId, {
        topic: topic.trim() || null,
        numQuestions,
      });
      if (!result.id || result.questions.length === 0) {
        setNoMaterials(true);
        return;
      }
      setQuiz(result);
      setAnswers(new Array(result.questions.length).fill(null));
      setPhase("taking");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't generate a quiz. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!quiz?.id || answers.some((a) => a === null) || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await submitAttempt(courseId, quiz.id, {
        studentId,
        answers: answers as number[],
      });
      setAttempt(result);
      setPhase("results");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't submit the quiz. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Practice quiz</h1>
          <p className="mt-2 text-muted-foreground">
            Generate a quiz from class{" "}
            <span className="font-medium text-foreground">{courseId}</span>'s materials and get
            scored, explained feedback.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/course">Back to class</Link>
        </Button>
      </div>

      {error && (
        <div
          role="alert"
          className="mt-6 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      {phase === "config" && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-xl">New quiz</CardTitle>
          </CardHeader>
          <CardContent>
            {noMaterials ? (
              <div role="alert" className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  There are no materials to quiz on yet. Upload some PDFs first.
                </p>
                <Button asChild>
                  <Link to="/upload">Upload materials</Link>
                </Button>
              </div>
            ) : (
              <form onSubmit={handleGenerate} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="topic">Topic (optional)</Label>
                  <Input
                    id="topic"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. photosynthesis — leave blank for a broad quiz"
                    maxLength={200}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="numQuestions">Number of questions</Label>
                  <select
                    id="numQuestions"
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    {QUESTION_COUNTS.map((n) => (
                      <option key={n} value={n}>
                        {n} questions
                      </option>
                    ))}
                  </select>
                </div>
                <Button type="submit" disabled={busy}>
                  {busy ? (
                    <>
                      <Loader2 className="animate-spin" aria-hidden="true" />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Sparkles aria-hidden="true" />
                      Generate quiz
                    </>
                  )}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      )}

      {phase === "taking" && quiz && (
        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          {quiz.questions.map((q, qi) => (
            <Card key={qi}>
              <CardContent className="pt-6">
                <fieldset>
                  <legend className="mb-3 font-medium">
                    {qi + 1}. {q.stem}
                  </legend>
                  <div className="space-y-2">
                    {q.options.map((opt, oi) => (
                      <label
                        key={oi}
                        className={cn(
                          "flex cursor-pointer items-center gap-3 rounded-md border p-3 text-sm transition-colors hover:bg-accent/50",
                          answers[qi] === oi && "border-primary bg-accent/50",
                        )}
                      >
                        <input
                          type="radio"
                          name={`q-${qi}`}
                          checked={answers[qi] === oi}
                          onChange={() =>
                            setAnswers((prev) => prev.map((a, i) => (i === qi ? oi : a)))
                          }
                          className="size-4 accent-primary"
                        />
                        {opt}
                      </label>
                    ))}
                  </div>
                </fieldset>
              </CardContent>
            </Card>
          ))}

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={busy || answers.some((a) => a === null)}>
              {busy ? (
                <>
                  <Loader2 className="animate-spin" aria-hidden="true" />
                  Submitting…
                </>
              ) : (
                "Submit answers"
              )}
            </Button>
            <Button type="button" variant="ghost" onClick={reset}>
              Start over
            </Button>
          </div>
        </form>
      )}

      {phase === "results" && attempt && (
        <div className="mt-8 space-y-6">
          <Card>
            <CardContent className="flex flex-col items-center gap-1 py-8 text-center">
              <p className="text-sm text-muted-foreground">You scored</p>
              <p className="text-4xl font-bold">
                {attempt.score} / {attempt.total}
              </p>
            </CardContent>
          </Card>

          <ol className="space-y-4">
            {attempt.results.map((r, qi) => (
              <li key={qi}>
                <Card>
                  <CardContent className="space-y-3 pt-6">
                    <p className="flex items-start gap-2 font-medium">
                      {r.is_correct ? (
                        <CheckCircle2
                          className="mt-0.5 size-5 shrink-0 text-success"
                          aria-hidden="true"
                        />
                      ) : (
                        <XCircle
                          className="mt-0.5 size-5 shrink-0 text-destructive"
                          aria-hidden="true"
                        />
                      )}
                      <span>
                        {qi + 1}. {r.stem}
                      </span>
                    </p>
                    <ul className="space-y-2">
                      {r.options.map((opt, oi) => {
                        const isCorrect = oi === r.correct_index;
                        const isYours = oi === r.your_answer;
                        return (
                          <li
                            key={oi}
                            className={cn(
                              "rounded-md border p-2.5 text-sm",
                              isCorrect && "border-success/50 bg-success/10",
                              isYours && !isCorrect && "border-destructive/50 bg-destructive/10",
                            )}
                          >
                            {opt}
                            {isCorrect && (
                              <span className="ml-2 text-xs font-medium text-success">
                                Correct answer
                              </span>
                            )}
                            {isYours && !isCorrect && (
                              <span className="ml-2 text-xs font-medium text-destructive">
                                Your answer
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                    {r.explanation && (
                      <p className="text-sm text-muted-foreground">{r.explanation}</p>
                    )}
                  </CardContent>
                </Card>
              </li>
            ))}
          </ol>

          <Button onClick={reset}>
            <Sparkles aria-hidden="true" />
            Take another quiz
          </Button>
        </div>
      )}
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { CircleAlert, FileText, Loader2, Send, Sparkles } from "lucide-react";
import * as React from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError, askQuestion, listDocuments, type Source } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useSession } from "@/session/session-context";

interface Turn {
  id: number;
  question: string;
  status: "pending" | "done" | "error";
  answer?: string;
  sources?: Source[];
  error?: string;
}

export function AskPage() {
  const { session } = useSession();
  const [turns, setTurns] = React.useState<Turn[]>([]);
  const [question, setQuestion] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const nextId = React.useRef(0);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  const courseId = session?.courseId ?? "";
  const documents = useQuery({
    queryKey: ["documents", courseId],
    queryFn: () => listDocuments(courseId),
    enabled: Boolean(courseId),
  });

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  // No session → back to join.
  if (!session) return <Navigate to="/" replace />;

  const filenameOf = (documentId: string): string => {
    const doc = documents.data?.find((d) => d.id === documentId);
    return doc?.filename ?? "Course material";
  };

  async function ask() {
    const trimmed = question.trim();
    if (!trimmed || busy) return;

    const id = nextId.current++;
    setTurns((prev) => [...prev, { id, question: trimmed, status: "pending" }]);
    setQuestion("");
    setBusy(true);
    try {
      const result = await askQuestion(courseId, trimmed);
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? { ...t, status: "done", answer: result.answer, sources: result.sources }
            : t,
        ),
      );
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Try again.";
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, status: "error", error: message } : t)),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ask your class</h1>
          <p className="mt-2 text-muted-foreground">
            Answers are grounded in class{" "}
            <span className="font-medium text-foreground">{courseId}</span>'s materials, with the
            sources they came from.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/course">Back to class</Link>
        </Button>
      </div>

      <div className="mt-8 space-y-6" aria-live="polite">
        {turns.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
              <Sparkles className="size-8 text-primary" aria-hidden="true" />
              <p className="font-medium">Ask your first question</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Try something specific from your course materials — the answer will cite where it
                came from.
              </p>
            </CardContent>
          </Card>
        ) : (
          turns.map((turn) => (
            <div key={turn.id} className="space-y-3">
              <div className="flex justify-end">
                <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-primary-foreground">
                  {turn.question}
                </p>
              </div>

              <div className="flex justify-start">
                <div className="max-w-[85%] space-y-3">
                  {turn.status === "pending" && (
                    <p className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                      Thinking…
                    </p>
                  )}

                  {turn.status === "error" && (
                    <p
                      role="alert"
                      className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
                    >
                      <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                      {turn.error}
                    </p>
                  )}

                  {turn.status === "done" && (
                    <>
                      <div className="whitespace-pre-wrap rounded-2xl rounded-bl-sm bg-muted px-4 py-3">
                        {turn.answer}
                      </div>
                      {turn.sources && turn.sources.length > 0 && (
                        <details className="rounded-md border bg-card px-4 py-2 text-sm">
                          <summary className="cursor-pointer font-medium">
                            Sources ({turn.sources.length})
                          </summary>
                          <ol className="mt-3 space-y-3">
                            {turn.sources.map((source, i) => (
                              <li key={i} className="space-y-1">
                                <p className="flex items-center gap-1.5 font-medium">
                                  <FileText
                                    className="size-3.5 shrink-0 text-primary"
                                    aria-hidden="true"
                                  />
                                  Source {i + 1} · {filenameOf(source.document_id)}
                                </p>
                                <p className="line-clamp-3 text-muted-foreground">{source.text}</p>
                              </li>
                            ))}
                          </ol>
                        </details>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask();
        }}
        className="sticky bottom-0 mt-6 bg-background/80 py-4 backdrop-blur"
      >
        <label htmlFor="question" className="sr-only">
          Your question
        </label>
        <div className="flex items-end gap-2">
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void ask();
              }
            }}
            rows={1}
            placeholder="Ask a question about the course materials…"
            className="flex max-h-40 min-h-10 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
          <Button type="submit" size="icon" disabled={busy || question.trim().length === 0}>
            {busy ? (
              <Loader2 className="animate-spin" aria-hidden="true" />
            ) : (
              <Send aria-hidden="true" />
            )}
            <span className="sr-only">Send question</span>
          </Button>
        </div>
      </form>
    </div>
  );
}

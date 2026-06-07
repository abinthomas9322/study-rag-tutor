import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, FileText, Loader2 } from "lucide-react";
import * as React from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError, listDocuments, uploadDocument } from "@/api/client";
import { FileDropzone } from "@/components/file-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useSession } from "@/session/session-context";

interface UploadItem {
  id: number;
  name: string;
  status: "uploading" | "error";
  error?: string;
}

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

export function UploadPage() {
  const { session } = useSession();
  const queryClient = useQueryClient();
  const [uploads, setUploads] = React.useState<UploadItem[]>([]);
  const [rejected, setRejected] = React.useState<string[]>([]);
  const nextId = React.useRef(0);

  const courseId = session?.courseId ?? "";
  const documents = useQuery({
    queryKey: ["documents", courseId],
    queryFn: () => listDocuments(courseId),
    enabled: Boolean(courseId),
  });

  // No session → back to join.
  if (!session) return <Navigate to="/" replace />;

  async function handleFiles(files: File[]) {
    const pdfs = files.filter(isPdf);
    setRejected(files.filter((f) => !isPdf(f)).map((f) => f.name));

    for (const file of pdfs) {
      const id = nextId.current++;
      setUploads((prev) => [...prev, { id, name: file.name, status: "uploading" }]);
      try {
        await uploadDocument(courseId, file);
        // Done — drop it from the queue; it now appears in the refetched list.
        setUploads((prev) => prev.filter((u) => u.id !== id));
        await queryClient.invalidateQueries({ queryKey: ["documents", courseId] });
      } catch (err) {
        const message = err instanceof ApiError ? err.message : "Upload failed. Please try again.";
        setUploads((prev) =>
          prev.map((u) => (u.id === id ? { ...u, status: "error", error: message } : u)),
        );
      }
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Upload materials</h1>
          <p className="mt-2 text-muted-foreground">
            Add PDFs to class <span className="font-medium text-foreground">{courseId}</span>. They
            are chunked, embedded, and made searchable for everyone.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/course">Back to class</Link>
        </Button>
      </div>

      <div className="mt-8">
        <FileDropzone onFiles={handleFiles} />
      </div>

      {rejected.length > 0 && (
        <div
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>Skipped non-PDF file(s): {rejected.join(", ")}</span>
        </div>
      )}

      {uploads.length > 0 && (
        <ul className="mt-4 space-y-2" aria-label="Uploads in progress">
          {uploads.map((u) => (
            <li
              key={u.id}
              className="flex items-center gap-3 rounded-md border bg-card p-3 text-sm"
            >
              {u.status === "uploading" ? (
                <Loader2
                  className="size-4 shrink-0 animate-spin text-muted-foreground"
                  aria-hidden="true"
                />
              ) : (
                <CircleAlert className="size-4 shrink-0 text-destructive" aria-hidden="true" />
              )}
              <span className="truncate font-medium">{u.name}</span>
              <span className={u.status === "error" ? "text-destructive" : "text-muted-foreground"}>
                {u.status === "uploading" ? "Uploading…" : u.error}
              </span>
            </li>
          ))}
        </ul>
      )}

      <section aria-labelledby="materials-heading" className="mt-10">
        <h2 id="materials-heading" className="text-lg font-semibold">
          Course materials
        </h2>

        {documents.isPending ? (
          <p className="mt-4 text-sm text-muted-foreground" role="status">
            Loading materials…
          </p>
        ) : documents.isError ? (
          <p className="mt-4 text-sm text-destructive" role="alert">
            Couldn't load the materials list.
          </p>
        ) : documents.data.length === 0 ? (
          <Card className="mt-4">
            <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
              <FileText className="size-8 text-muted-foreground" aria-hidden="true" />
              <p className="font-medium">No materials yet</p>
              <p className="text-sm text-muted-foreground">
                Upload the first PDF to start building this class's knowledge base.
              </p>
            </CardContent>
          </Card>
        ) : (
          <ul className="mt-4 space-y-2">
            {documents.data.map((doc) => (
              <li key={doc.id} className="flex items-center gap-3 rounded-md border bg-card p-3">
                <FileText className="size-5 shrink-0 text-primary" aria-hidden="true" />
                <span className="flex-1 truncate font-medium">{doc.filename}</span>
                <span className="text-sm text-muted-foreground">{doc.num_chunks} chunks</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

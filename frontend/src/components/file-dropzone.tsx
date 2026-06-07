import { UploadCloud } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

/**
 * An accessible file picker: a real (visually-hidden but focusable) file input
 * with a labelled drop area. Clicking or keyboard-activating the label opens
 * the picker; drag-and-drop is a progressive enhancement on top.
 */
export function FileDropzone({ onFiles, disabled }: FileDropzoneProps) {
  const [dragActive, setDragActive] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  function emit(list: FileList | null) {
    if (list && list.length > 0) onFiles(Array.from(list));
  }

  return (
    <div
      onDragOver={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragActive(false);
        emit(e.dataTransfer.files);
      }}
      className={cn(
        "rounded-lg border-2 border-dashed transition-colors",
        dragActive ? "border-primary bg-accent/50" : "border-input",
        disabled && "opacity-60",
      )}
    >
      <label
        htmlFor="file-upload"
        className="flex cursor-pointer flex-col items-center gap-3 px-6 py-12 text-center focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2"
      >
        <UploadCloud className="size-10 text-muted-foreground" aria-hidden="true" />
        <span className="font-medium">Drag PDFs here, or click to browse</span>
        <span className="text-sm text-muted-foreground">Only PDF files are supported</span>
        <input
          id="file-upload"
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          disabled={disabled}
          className="sr-only"
          onChange={(e) => {
            emit(e.target.files);
            e.target.value = ""; // allow re-selecting the same file
          }}
        />
      </label>
    </div>
  );
}

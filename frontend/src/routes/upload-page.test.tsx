import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  fetchHealth,
  listDocuments,
  uploadDocument,
  type CourseDocument,
} from "@/api/client";
import { renderApp } from "@/test/utils";

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    fetchHealth: vi.fn(),
    listDocuments: vi.fn(),
    uploadDocument: vi.fn(),
  };
});

const mockedList = vi.mocked(listDocuments);
const mockedUpload = vi.mocked(uploadDocument);

const DOC: CourseDocument = {
  id: "d1",
  course_id: "CS101",
  filename: "week1.pdf",
  num_chunks: 12,
  uploaded_at: "2026-06-07",
};

function pdf(name = "week1.pdf"): File {
  return new File(["%PDF-1.4 fake"], name, { type: "application/pdf" });
}

beforeEach(() => {
  vi.mocked(fetchHealth).mockResolvedValue({ status: "ok" });
  localStorage.setItem(
    "study-rag-session",
    JSON.stringify({
      courseId: "CS101",
      student: { id: 1, course_id: "CS101", display_name: "Alex", joined_at: "2026-01-01" },
    }),
  );
});

afterEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
});

describe("UploadPage", () => {
  it("redirects to join when there is no session", () => {
    localStorage.clear();
    mockedList.mockResolvedValue([]);
    renderApp("/upload");
    expect(screen.getByRole("heading", { level: 1, name: /join your class/i })).toBeInTheDocument();
  });

  it("shows an empty state when there are no documents", async () => {
    mockedList.mockResolvedValue([]);
    renderApp("/upload");
    expect(await screen.findByText(/no materials yet/i)).toBeInTheDocument();
  });

  it("lists existing documents with their chunk counts", async () => {
    mockedList.mockResolvedValue([DOC]);
    renderApp("/upload");
    expect(await screen.findByText("week1.pdf")).toBeInTheDocument();
    expect(screen.getByText(/12 chunks/i)).toBeInTheDocument();
  });

  it("uploads a PDF and shows it in the refreshed list", async () => {
    const user = userEvent.setup();
    mockedList.mockResolvedValueOnce([]).mockResolvedValue([DOC]);
    mockedUpload.mockResolvedValue(DOC);
    renderApp("/upload");
    await screen.findByText(/no materials yet/i);

    await user.upload(screen.getByLabelText(/drag pdfs here/i), pdf());

    expect(await screen.findByText("week1.pdf")).toBeInTheDocument();
    expect(mockedUpload).toHaveBeenCalledWith("CS101", expect.any(File));
  });

  it("rejects non-PDF files without calling the API", async () => {
    // applyAccept:false simulates a non-PDF arriving (e.g. via drag-drop, which
    // doesn't enforce the input's accept filter) so the client-side guard runs.
    const user = userEvent.setup({ applyAccept: false });
    mockedList.mockResolvedValue([]);
    renderApp("/upload");
    await screen.findByText(/no materials yet/i);

    const notes = new File(["hi"], "notes.txt", { type: "text/plain" });
    await user.upload(screen.getByLabelText(/drag pdfs here/i), notes);

    expect(await screen.findByText(/skipped non-pdf/i)).toBeInTheDocument();
    expect(mockedUpload).not.toHaveBeenCalled();
  });

  it("shows an error when an upload fails", async () => {
    const user = userEvent.setup();
    mockedList.mockResolvedValue([]);
    mockedUpload.mockRejectedValue(new ApiError(400, "no extractable text found in the PDF"));
    renderApp("/upload");
    await screen.findByText(/no materials yet/i);

    await user.upload(screen.getByLabelText(/drag pdfs here/i), pdf("scan.pdf"));

    expect(await screen.findByText(/no extractable text/i)).toBeInTheDocument();
  });
});

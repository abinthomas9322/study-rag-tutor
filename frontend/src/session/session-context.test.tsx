import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Providers } from "@/test/utils";
import { useSession, type Session } from "@/session/session-context";

const SESSION: Session = {
  courseId: "CS101",
  student: { id: 1, course_id: "CS101", display_name: "Alex", joined_at: "2026-01-01" },
};

afterEach(() => {
  localStorage.clear();
});

describe("session context", () => {
  it("starts with no session", () => {
    const { result } = renderHook(() => useSession(), { wrapper: Providers });
    expect(result.current.session).toBeNull();
  });

  it("starts and persists a session", () => {
    const { result } = renderHook(() => useSession(), { wrapper: Providers });
    act(() => result.current.startSession(SESSION));
    expect(result.current.session).toEqual(SESSION);
    expect(JSON.parse(localStorage.getItem("study-rag-session")!)).toEqual(SESSION);
  });

  it("ends and clears a session", () => {
    const { result } = renderHook(() => useSession(), { wrapper: Providers });
    act(() => result.current.startSession(SESSION));
    act(() => result.current.endSession());
    expect(result.current.session).toBeNull();
    expect(localStorage.getItem("study-rag-session")).toBeNull();
  });

  it("restores a persisted session on mount", () => {
    localStorage.setItem("study-rag-session", JSON.stringify(SESSION));
    const { result } = renderHook(() => useSession(), { wrapper: Providers });
    expect(result.current.session).toEqual(SESSION);
  });

  it("ignores malformed stored data", () => {
    localStorage.setItem("study-rag-session", "{not json");
    const { result } = renderHook(() => useSession(), { wrapper: Providers });
    expect(result.current.session).toBeNull();
  });
});

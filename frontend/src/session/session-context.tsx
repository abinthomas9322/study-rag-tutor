import * as React from "react";

import type { Student } from "@/api/client";

/** The active study session: which course the student joined, and as whom. */
export interface Session {
  courseId: string;
  student: Student;
}

interface SessionContextValue {
  session: Session | null;
  startSession: (session: Session) => void;
  endSession: () => void;
}

const STORAGE_KEY = "study-rag-session";

const SessionContext = React.createContext<SessionContextValue | undefined>(undefined);

function readStoredSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Session;
    if (parsed?.courseId && parsed?.student?.id) return parsed;
    return null;
  } catch {
    return null;
  }
}

/** Holds the joined-course session and persists it across reloads. */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = React.useState<Session | null>(readStoredSession);

  const startSession = React.useCallback((next: Session) => {
    setSession(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const endSession = React.useCallback(() => {
    setSession(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const value = React.useMemo<SessionContextValue>(
    () => ({ session, startSession, endSession }),
    [session, startSession, endSession],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = React.useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within a SessionProvider");
  return ctx;
}

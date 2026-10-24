import { useContext } from "react";
import { SessionContext, type SessionContextValue } from "../context/SessionContext";

export function useSessionContext(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSessionContext must be used inside a SessionProvider");
  }
  return ctx;
}


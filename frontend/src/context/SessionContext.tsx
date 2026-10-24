import { createContext, useState, type ReactNode } from "react";
import type { CitationItem } from "../types/api";

export type ProvenanceDrawerTab = "Doc" | "KG" | "Mem" | "Trace";

export interface SessionContextValue {
  activeSessionId: string;
  activeCitationId: string | null;
  isDrawerOpen: boolean;
  activeDrawerTab: ProvenanceDrawerTab;
  setActiveSessionId: (id: string) => void;
  openProvenanceForCitation: (citation: CitationItem) => void;
  setActiveDrawerTab: (tab: ProvenanceDrawerTab) => void;
  setIsDrawerOpen: (open: boolean) => void;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [activeSessionId, setActiveSessionId] = useState<string>("session-seed-001");
  const [activeCitationId, setActiveCitationId] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);
  const [activeDrawerTab, setActiveDrawerTab] = useState<ProvenanceDrawerTab>("Doc");

  const openProvenanceForCitation = (citation: CitationItem) => {
    setActiveCitationId(citation.badge_id);
    setActiveDrawerTab(citation.modality);
    setIsDrawerOpen(true);
  };

  return (
    <SessionContext.Provider
      value={{
        activeSessionId,
        activeCitationId,
        isDrawerOpen,
        activeDrawerTab,
        setActiveSessionId,
        openProvenanceForCitation,
        setActiveDrawerTab,
        setIsDrawerOpen,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}


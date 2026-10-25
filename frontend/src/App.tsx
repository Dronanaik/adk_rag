import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ProvenanceDrawer } from "./components/ui";
import { RoleProvider } from "./context/RoleContext";
import { SessionProvider } from "./context/SessionContext";
import { ThemeProvider } from "./context/ThemeContext";
import { useSessionContext } from "./hooks/useSessionContext";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { KnowledgeGraphExplorerPage } from "./pages/KnowledgeGraphExplorerPage";
import { MemoryInspectorPage } from "./pages/MemoryInspectorPage";
import { ResearchWorkspacePage } from "./pages/ResearchWorkspacePage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      retry: 1,
    },
  },
});

function WorkspaceRoutes() {
  const {
    isDrawerOpen,
    activeDrawerTab,
    activeCitationId,
    sessionCitations,
    sessionTraceSteps,
    setActiveDrawerTab,
    openProvenanceForCitation,
    setIsDrawerOpen,
  } = useSessionContext();

  return (
    <AppShell
      rightDrawer={
        <ProvenanceDrawer
          isOpen={isDrawerOpen}
          activeTab={activeDrawerTab}
          activeCitationId={activeCitationId}
          citations={sessionCitations}
          traceSteps={sessionTraceSteps}
          onTabChange={setActiveDrawerTab}
          onSelectCitation={openProvenanceForCitation}
          onClose={() => setIsDrawerOpen(false)}
        />
      }
    >
      <Routes>
        <Route path="/" element={<Navigate to="/workspace" replace />} />
        <Route path="/workspace" element={<ResearchWorkspacePage />} />
        <Route path="/documents" element={<KnowledgeBasePage />} />
        <Route path="/graph" element={<KnowledgeGraphExplorerPage />} />
        <Route path="/memory" element={<MemoryInspectorPage />} />
      </Routes>
    </AppShell>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <RoleProvider>
          <SessionProvider>
            <BrowserRouter>
              <WorkspaceRoutes />
            </BrowserRouter>
          </SessionProvider>
        </RoleProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

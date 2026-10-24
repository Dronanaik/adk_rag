import type { ReactNode } from "react";
import { LeftSidebarNav } from "./LeftSidebarNav";
import { TopHeaderBar } from "./TopHeaderBar";

export interface AppShellProps {
  children: ReactNode;
  rightDrawer?: ReactNode;
}

export function AppShell({ children, rightDrawer }: AppShellProps) {
  return (
    <div
      className="flex flex-col h-screen w-screen overflow-hidden"
      style={{ backgroundColor: "var(--bg-canvas)" }}
    >
      <TopHeaderBar />
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <LeftSidebarNav />
        <main className="flex-1 min-w-0 overflow-y-auto">{children}</main>
        {rightDrawer}
      </div>
    </div>
  );
}


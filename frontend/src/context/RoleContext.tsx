import { createContext, useState, type ReactNode } from "react";
import type { AppRole } from "../types/api";

export interface RoleContextValue {
  role: AppRole;
  adminApiKey: string;
  setRole: (nextRole: AppRole) => void;
  setAdminApiKey: (key: string) => void;
  isAdmin: boolean;
}

export const RoleContext = createContext<RoleContextValue | null>(null);

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<AppRole>("researcher");
  const [adminApiKey, setAdminApiKey] = useState<string>("");

  return (
    <RoleContext.Provider
      value={{
        role,
        adminApiKey,
        setRole,
        setAdminApiKey,
        isAdmin: role === "admin",
      }}
    >
      {children}
    </RoleContext.Provider>
  );
}


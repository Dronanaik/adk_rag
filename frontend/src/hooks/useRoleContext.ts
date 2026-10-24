import { useContext } from "react";
import { RoleContext, type RoleContextValue } from "../context/RoleContext";

export function useRoleContext(): RoleContextValue {
  const ctx = useContext(RoleContext);
  if (!ctx) {
    throw new Error("useRoleContext must be used inside a RoleProvider");
  }
  return ctx;
}


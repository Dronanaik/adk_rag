import { useContext } from "react";
import { ThemeContext, type ThemeContextValue } from "../context/ThemeContext";

export function useThemeContext(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useThemeContext must be used inside a ThemeProvider");
  }
  return ctx;
}


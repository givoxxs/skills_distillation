"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

/* Minimal theme provider — same shape as next-themes' useTheme() so callers
 * keep working, but without next-themes' <script> injection that React 19 /
 * Next 16 now flags. State lives in localStorage and the `data-theme`
 * attribute on <html>; the initial render is always "light" to avoid
 * SSR / client mismatch, then the effect swaps to the stored preference. */

export type Theme = "light" | "dark";

type Ctx = {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggle: () => void;
};

const ThemeContext = createContext<Ctx | null>(null);

const STORAGE_KEY = "sdl:theme";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    // Bootstrap script in <head> already set data-theme from localStorage
    // before paint — read that back so state matches reality and we don't
    // overwrite the user's choice.
    const attr = document.documentElement.getAttribute("data-theme");
    if (attr === "light" || attr === "dark") {
      setThemeState(attr);
      return;
    }
    // No attribute yet: try localStorage directly (rare — only when the
    // bootstrap script is somehow blocked).
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw === "light" || raw === "dark") {
        setThemeState(raw);
        document.documentElement.setAttribute("data-theme", raw);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    document.documentElement.setAttribute("data-theme", t);
    try {
      window.localStorage.setItem(STORAGE_KEY, t);
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = useCallback(() => {
    setTheme(theme === "light" ? "dark" : "light");
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

/* Drop-in replacement for next-themes' useTheme(): exposes `theme` and
 * `setTheme` so existing call sites need no rewrite. */
export function useTheme(): { theme: Theme; setTheme: (t: Theme) => void; toggle: () => void } {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    return {
      theme: "light",
      setTheme: () => {},
      toggle: () => {},
    };
  }
  return ctx;
}

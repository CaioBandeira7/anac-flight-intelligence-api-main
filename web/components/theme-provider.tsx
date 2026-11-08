"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react";

export type Theme = "day" | "night";
export const THEME_KEY = "fi-theme";
export const DEFAULT_THEME: Theme = "day";

/**
 * Runs before paint (inlined in <head>) so the saved theme is applied without a
 * flash. Kept tiny and dependency-free; one theme system for the whole app.
 */
export const THEME_BOOT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");document.documentElement.dataset.theme=(t==="night"||t==="day")?t:"${DEFAULT_THEME}"}catch(e){document.documentElement.dataset.theme="${DEFAULT_THEME}"}})();`;

interface ThemeCtx {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggle: () => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

function readTheme(): Theme {
  const t = document.documentElement.dataset.theme;
  return t === "night" || t === "day" ? t : DEFAULT_THEME;
}

// <html data-theme> is the single source of truth; React subscribes to it.
function subscribe(onChange: () => void) {
  const mo = new MutationObserver(onChange);
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => mo.disconnect();
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useSyncExternalStore(subscribe, readTheme, () => DEFAULT_THEME);

  const setTheme = useCallback((t: Theme) => {
    document.documentElement.dataset.theme = t;
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch {
      /* storage unavailable: the choice lasts for this visit only */
    }
  }, []);
  const toggle = useCallback(() => setTheme(readTheme() === "day" ? "night" : "day"), [setTheme]);
  const value = useMemo(() => ({ theme, setTheme, toggle }), [theme, setTheme, toggle]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}

/** Sky colours for the CloudShader, per theme. Deep enough that glass panels keep contrast. */
export const SKY: Record<Theme, { skyTopColor: string; skyBottomColor: string; cloudColor: string; sunColor: string; sunIntensity: number; speed: number }> = {
  day: { skyTopColor: "#1a4c8e", skyBottomColor: "#4a86c4", cloudColor: "#e6eef8", sunColor: "#fff2d1", sunIntensity: 0.22, speed: 0.8 },
  night: { skyTopColor: "#040914", skyBottomColor: "#12264a", cloudColor: "#3b5175", sunColor: "#c9d7ff", sunIntensity: 0.1, speed: 0.6 },
};

"use client";

import { Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme, type Theme } from "@/components/theme-provider";

const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "day", label: "Day", icon: Sun },
  { value: "night", label: "Night", icon: Moon },
];

/** DAY / NIGHT segmented switch. */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  return (
    <div role="group" aria-label="Theme" className={cn("flex items-center rounded-full border border-line bg-glass p-0.5 backdrop-blur-xl", className)}>
      {OPTIONS.map((o) => {
        const on = theme === o.value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => setTheme(o.value)}
            className={cn(
              "flex h-8 items-center gap-1.5 rounded-full px-3 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors",
              on ? "bg-primary text-primary-foreground shadow-sm" : "text-muted hover:text-ink",
            )}
          >
            <o.icon className="size-3.5" aria-hidden />
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

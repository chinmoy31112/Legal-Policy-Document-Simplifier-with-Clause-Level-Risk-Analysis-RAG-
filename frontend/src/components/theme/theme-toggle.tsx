"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Sun, Moon, Laptop } from "lucide-react";

const subscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const mounted = React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  if (!mounted) {
    return (
      <div
        className={`h-9 w-9 rounded-[10px] border border-[var(--border)] bg-[var(--soft-surface)] opacity-50 ${className}`}
        aria-hidden="true"
      />
    );
  }

  const cycleTheme = () => {
    if (theme === "light") {
      setTheme("dark");
    } else if (theme === "dark") {
      setTheme("system");
    } else {
      setTheme("light");
    }
  };

  const currentLabel =
    theme === "light"
      ? "Light (Calm Paper)"
      : theme === "dark"
      ? "Dark (Midnight Focus)"
      : "System";

  return (
    <button
      type="button"
      onClick={cycleTheme}
      aria-label={`Toggle color theme. Current theme is ${currentLabel}`}
      title={`Current: ${currentLabel}. Click to switch theme.`}
      className={`relative inline-flex items-center justify-center h-9 px-3 gap-2 rounded-[10px] text-xs font-medium border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--soft-surface)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 ${className}`}
    >
      {theme === "light" && <Sun className="h-4 w-4 text-[#B4532A]" />}
      {theme === "dark" && <Moon className="h-4 w-4 text-[#8B9BFF]" />}
      {theme === "system" && <Laptop className="h-4 w-4 text-[var(--muted-foreground)]" />}
      <span className="capitalize">{theme ?? "system"}</span>
    </button>
  );
}

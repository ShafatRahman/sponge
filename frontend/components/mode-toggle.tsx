"use client";

import type { JobMode } from "@/lib/models/job";

interface ModeToggleProps {
  mode: JobMode;
  onModeChange: (mode: JobMode) => void;
  disabled?: boolean;
}

export function ModeToggle({ mode, onModeChange, disabled }: ModeToggleProps) {
  return (
    <div className="flex items-center justify-center gap-3">
      <button
        type="button"
        onClick={() => onModeChange("default")}
        disabled={disabled}
        className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
          mode === "default"
            ? "bg-foreground/10 text-foreground ring-foreground/20 ring-1"
            : "text-muted-foreground hover:text-foreground"
        } disabled:opacity-50`}
      >
        Standard
      </button>
      <button
        type="button"
        onClick={() => onModeChange("detailed")}
        disabled={disabled}
        className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
          mode === "detailed"
            ? "bg-foreground/10 text-foreground ring-foreground/20 ring-1"
            : "text-muted-foreground hover:text-foreground"
        } disabled:opacity-50`}
      >
        Detailed
      </button>
      <span className="text-muted-foreground text-xs">
        {mode === "default" ? "AI-enhanced index of your site" : "Full content + AI descriptions"}
      </span>
    </div>
  );
}

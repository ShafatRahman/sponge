"use client";

import { Badge } from "@/components/ui/badge";
import type { Progress, JobStatus } from "@/lib/models/job";

interface GenerationProgressProps {
  status: JobStatus;
  progress: Progress | null;
}

const PHASE_LABELS: Record<string, string> = {
  pending: "Queued",
  discovering: "Discovering pages",
  extracting: "Extracting content",
  enhancing: "Enhancing with AI",
  generating: "Building llms.txt",
  completed: "Complete",
  failed: "Failed",
};

const PHASE_ORDER = [
  "pending",
  "discovering",
  "extracting",
  "enhancing",
  "generating",
  "completed",
];

function getPhaseIndex(phase: string): number {
  const idx = PHASE_ORDER.indexOf(phase);
  return idx >= 0 ? idx : 0;
}

export function GenerationProgress({ status, progress }: GenerationProgressProps) {
  const currentIndex = getPhaseIndex(status);
  const totalSteps = PHASE_ORDER.length - 1;
  const progressPercent = Math.min((currentIndex / totalSteps) * 100, 100);
  const isWaiting = status === "pending" && !progress;

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${isWaiting ? "animate-pulse" : ""}`}>
            {PHASE_LABELS[status] ?? status}
          </span>
          <Badge variant={status === "completed" ? "default" : "secondary"}>
            {Math.round(progressPercent)}%
          </Badge>
        </div>
        <div className="bg-secondary h-1.5 w-full overflow-hidden rounded-full">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${
              isWaiting ? "bg-muted-foreground/40 animate-pulse" : "bg-primary"
            }`}
            style={{ width: isWaiting ? "5%" : `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Phase steps */}
      <div className="space-y-3">
        {PHASE_ORDER.slice(1, -1).map((phase, i) => {
          const phaseIndex = i + 1;
          const isActive = phaseIndex === currentIndex;
          const isComplete = phaseIndex < currentIndex;
          const isPending = phaseIndex > currentIndex;

          return (
            <div key={phase} className="flex items-center gap-3">
              <div
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
                  isComplete
                    ? "bg-primary text-primary-foreground"
                    : isActive
                      ? "bg-primary/20 text-primary ring-primary/50 ring-1"
                      : "bg-secondary text-muted-foreground"
                }`}
              >
                {isComplete ? "\u2713" : phaseIndex}
              </div>
              <div className="min-w-0 flex-1">
                <p
                  className={`text-sm ${
                    isActive
                      ? "text-foreground font-medium"
                      : isPending
                        ? "text-muted-foreground"
                        : "text-foreground"
                  }`}
                >
                  {PHASE_LABELS[phase]}
                </p>
                {isActive && (
                  <p
                    className={`text-muted-foreground truncate text-xs ${!progress?.message ? "animate-pulse" : ""}`}
                  >
                    {progress?.message ?? "Connecting to worker..."}
                  </p>
                )}
                {isActive && progress?.completed != null && progress?.total != null && (
                  <p className="text-muted-foreground text-xs">
                    {progress.completed} / {progress.total} pages
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

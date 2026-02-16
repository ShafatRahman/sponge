"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { CaseTransformer } from "@/lib/utils/case-transform";
import { JobStatusResponseSchema } from "@/lib/models/job";
import type { JobStatusResponse } from "@/lib/models/job";

interface UseJobStreamReturn {
  data: JobStatusResponse | null;
  error: string | null;
  isConnected: boolean;
  isTimedOut: boolean;
}

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

/** How long (ms) to wait with no progress change before considering the job stalled. */
const STALL_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Hook that subscribes to a Server-Sent Events stream for real-time
 * job progress updates. Replaces polling entirely.
 *
 * - Connects to GET /api/jobs/{jobId}/stream/
 * - Parses progress and complete events
 * - Transforms snake_case -> camelCase
 * - Auto-closes on terminal status
 * - Cleans up EventSource on unmount
 * - Times out after 5 minutes of no progress change
 */
export function useJobStream(jobId: string): UseJobStreamReturn {
  const [data, setData] = useState<JobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isTimedOut, setIsTimedOut] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const lastProgressRef = useRef<number>(0);
  const stallTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleEvent = useCallback(
    (raw: unknown) => {
      // Reset the stall timer on every meaningful event
      lastProgressRef.current = Date.now();

      const transformed = CaseTransformer.snakeToCamel(raw);
      const parsed = JobStatusResponseSchema.safeParse(transformed);
      if (parsed.success) {
        setData(parsed.data);
      } else {
        // Partial progress event -- merge with existing data
        setData((prev) => {
          if (!prev) {
            return {
              id: jobId,
              status: (transformed as Record<string, string>).phase ?? "pending",
              progress: transformed as JobStatusResponse["progress"],
              result: null,
              error: null,
            } as JobStatusResponse;
          }
          const phase = (transformed as Record<string, string>).phase;
          return {
            ...prev,
            status: phase ?? prev.status,
            progress: transformed as JobStatusResponse["progress"],
          } as JobStatusResponse;
        });
      }
    },
    [jobId],
  );

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    const url = `${apiUrl}/api/jobs/${jobId}/stream/`;
    const es = new EventSource(url);
    eventSourceRef.current = es;
    lastProgressRef.current = Date.now();

    // Stall detection: check every 10s whether the last progress event
    // was received within the timeout window.
    stallTimerRef.current = setInterval(() => {
      const elapsed = Date.now() - lastProgressRef.current;
      if (elapsed >= STALL_TIMEOUT_MS) {
        setIsTimedOut(true);
        setError("The job appears to have stalled. Please try again.");
        setIsConnected(false);
        es.close();
        if (stallTimerRef.current) clearInterval(stallTimerRef.current);
      }
    }, 10_000);

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.addEventListener("progress", (event: MessageEvent) => {
      try {
        const raw = JSON.parse(event.data);
        handleEvent(raw);
      } catch {
        // Ignore malformed events
      }
    });

    es.addEventListener("complete", (event: MessageEvent) => {
      try {
        const raw = JSON.parse(event.data);
        const transformed = CaseTransformer.snakeToCamel(raw);
        const parsed = JobStatusResponseSchema.safeParse(transformed);
        if (parsed.success) {
          setData(parsed.data);
        }
      } catch {
        // Ignore malformed events
      }
      // Close connection on terminal event
      es.close();
      setIsConnected(false);
      if (stallTimerRef.current) clearInterval(stallTimerRef.current);
    });

    es.addEventListener("error", (event: MessageEvent) => {
      try {
        const raw = JSON.parse(event.data);
        const errorMsg = (raw as { error?: string }).error ?? "Stream error";
        setError(errorMsg);
        // Close the stream on server-reported error events
        es.close();
        setIsConnected(false);
        if (stallTimerRef.current) clearInterval(stallTimerRef.current);
      } catch {
        // Ignore malformed events
      }
    });

    es.onerror = () => {
      setIsConnected(false);
      // EventSource auto-reconnects on transient errors unless closed
      // If the job reached terminal state, we don't need to reconnect
      setData((prev) => {
        if (prev && TERMINAL_STATUSES.has(prev.status)) {
          es.close();
          if (stallTimerRef.current) clearInterval(stallTimerRef.current);
        }
        return prev;
      });
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      setIsConnected(false);
      if (stallTimerRef.current) clearInterval(stallTimerRef.current);
    };
  }, [jobId, handleEvent]);

  return { data, error, isConnected, isTimedOut };
}
